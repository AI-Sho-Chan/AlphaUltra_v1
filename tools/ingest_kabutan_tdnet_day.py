import argparse, pathlib, time, hashlib, re, os
import pandas as pd
from urllib.parse import urlparse
try:
    import requests
except Exception:
    requests = None

ROOT = pathlib.Path(r"C:\AI\AlphaUltra")
RAW  = ROOT/"data/raw/kabutan"
BRZ  = ROOT/"data/bronze/tdnet"

def _pick(cols, *cands):
    low={c.lower():c for c in cols}
    for k in cands:
        if k in low: return low[k]
    return None

def _norm(df: pd.DataFrame) -> pd.DataFrame:
    cols=df.columns
    dcol=_pick(cols,"date","日付")
    tcol=_pick(cols,"time","時刻","公表時刻")
    ccol=_pick(cols,"code","証券コード","銘柄コード")
    ncol=_pick(cols,"company","会社名","銘柄名")
    hcol=_pick(cols,"headline","タイトル","件名")
    ucol=_pick(cols,"url","リンク","詳細リンク")
    acol=_pick(cols,"attach_url","添付","資料リンク")
    cat =_pick(cols,"category","区分","種類")

    out=pd.DataFrame()
    dt=(df[dcol].astype(str).str.strip() if dcol else "")
    tm=(df[tcol].astype(str).str.strip() if tcol else "00:00")
    out["published_at"]=pd.to_datetime((dt+" "+tm).str.strip(), errors="coerce")
    out["ticker"]=df[ccol].astype(str).str.strip() if ccol else ""
    out["company"]=df[ncol].astype(str).str.strip() if ncol else ""
    out["category"]=df[cat ].astype(str).str.strip() if cat else ""
    out["headline"]=df[hcol].astype(str).str.strip() if hcol else ""
    out["url"]     =df[ucol].astype(str).str.strip() if ucol else ""
    out["attach_url"]=df[acol].astype(str).str.strip() if acol else ""
    src_key=(out["url"].fillna("")+"|"+out["published_at"].astype(str))
    out["source_id"]=src_key.apply(lambda s: hashlib.sha1(s.encode("utf-8")).hexdigest())
    return out

def _fetch_pdf(url: str, outdir: pathlib.Path, cookie: str="") -> str:
    if not (requests and url): return ""
    try:
        headers={"User-Agent":"Mozilla/5.0"}
        if cookie: headers["Cookie"]=cookie
        r=requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        name = pathlib.Path(urlparse(url).path).name or "attach.pdf"
        name = re.sub(r"[^A-Za-z0-9_.-]+","_", name)
        fp=outdir/name; fp.write_bytes(r.content); return str(fp)
    except Exception:
        return ""

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--date", required=True)                 # YYYY-MM-DD
    ap.add_argument("--src",  default=str(RAW))              # data/raw/kabutan/{date}/*.csv 等
    ap.add_argument("--out",  default=str(BRZ/"tdnet_day.parquet"))
    ap.add_argument("--download-attachments", action="store_true")
    args=ap.parse_args()

    daydir = pathlib.Path(args.src)/args.date
    files  = list(daydir.glob("*.csv"))+list(daydir.glob("*.tsv"))+list(daydir.glob("*.xlsx"))
    parts=[]
    for p in files:
        try:
            if p.suffix==".xlsx": df=pd.read_excel(p)
            elif p.suffix==".tsv": df=pd.read_csv(p, sep="\t")
            else: df=pd.read_csv(p)
            nd=_norm(df); nd["raw_file"]=p.name; parts.append(nd)
        except Exception as e:
            print("[tdnet-day] skip", p, e)
    if not parts:
        print("[tdnet-day] no files in", daydir); return

    out=pd.concat(parts, ignore_index=True).dropna(subset=["published_at","ticker"], how="any")
    if args.download_attachments and out["attach_url"].fillna("").str.len().gt(0).any():
        cookie=os.getenv("KABUTAN_COOKIE","")
        attach_dir = daydir/"attachments"; attach_dir.mkdir(parents=True, exist_ok=True)
        out["attach_path"]=out["attach_url"].fillna("").apply(lambda u:_fetch_pdf(u, attach_dir, cookie) if u else "")

    pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(args.out, index=False)
    print("[tdnet-day] wrote", args.out, "rows=", len(out))

if __name__=="__main__": main()
