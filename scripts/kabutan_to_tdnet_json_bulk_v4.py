import re, json, hashlib
from pathlib import Path
import pandas as pd

SRC = Path(r"C:\AI\AlphaUltra_v1\data\raw\kabutan")
DST = Path(r"C:\AI\AlphaUltra_v1\data\raw\tdnet"); DST.mkdir(parents=True, exist_ok=True)

PRICE_KEYS = {"open","high","low","close","始値","高値","安値","終値"}

def find_ymd(p: Path):
    s=str(p)
    m=re.search(r"(20\d{2})[-_/](\d{2})[-_/](\d{2})", s)
    if m: return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    parts=p.parts
    for i in range(len(parts)-2):
        if re.fullmatch(r"20\d{2}", parts[i]) and re.fullmatch(r"\d{2}", parts[i+1]) and re.fullmatch(r"\d{2}", parts[i+2]):
            return f"{parts[i]}-{parts[i+1]}-{parts[i+2]}"
    m=re.search(r"(20\d{2})(\d{2})(\d{2})", s)
    if m: return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return None

def pick_col(cols, keys):
    m={c.lower().strip():c for c in cols}
    for k in keys:
        for low,orig in m.items():
            if k in low: return orig
    return None

files = [*SRC.rglob("*tdnet*.csv"), *SRC.rglob("tdnet.csv"), *SRC.rglob("*.CSV"), *SRC.rglob("*tdnet*.tsv")]
written=0
for fp in files:
    try:
        if fp.suffix.lower()==".tsv":
            df=pd.read_csv(fp, sep="\t", encoding="utf-8-sig")
        else:
            try: df=pd.read_csv(fp, encoding="utf-8-sig")
            except UnicodeDecodeError: df=pd.read_csv(fp, encoding="cp932")
    except Exception:
        continue

    # 価格テーブルは除外
    low={c.lower() for c in df.columns}
    if len(PRICE_KEYS & low)>=3: 
        continue

    c_code=pick_col(df.columns, ["コード","銘柄コード","code"])
    c_title=pick_col(df.columns, ["タイトル","件名","title","表題"])
    c_dt=pick_col(df.columns, ["掲載日時","発表日時","公表日時","日時","date","datetime","published","time"])
    c_d =pick_col(df.columns, ["掲載日","発表日","公表日","日付","date"])
    c_t =pick_col(df.columns, ["掲載時刻","発表時刻","公表時刻","時刻","time"])
    c_body=pick_col(df.columns, ["本文","内容","テキスト","body"])
    c_url =pick_col(df.columns, ["url","詳細","link"])
    c_pdf =pick_col(df.columns, ["pdf"])
    if not (c_code and c_title): 
        continue

    # 日時の列→なければフォルダ日付で補完
    dt = None
    if c_dt:
        dt = pd.to_datetime(df[c_dt], errors="coerce")
    else:
        d = pd.to_datetime(df[c_d], errors="coerce") if c_d else None
        t = df[c_t].astype(str) if c_t else None
        if d is not None:
            dt = pd.to_datetime(d.astype(str)+" "+(t if t is not None else ""), errors="coerce")
    ymd = find_ymd(fp)
    if ymd:
        fill = pd.to_datetime(ymd+" 15:00:00")
        if dt is None:
            dt = pd.Series([fill]*len(df))
        else:
            dt = pd.to_datetime(dt).fillna(fill)
    if dt is None:
        continue

    code=df[c_code].astype(str)
    title=df[c_title].astype(str)
    code4=code.str.extract(r"(\d{4})", expand=False)
    keep=(~dt.isna()) & code4.notna() & title.notna()
    if not keep.any(): 
        continue

    body=(df[c_body].astype(str) if c_body else pd.Series([""]*len(df)))[keep]
    url =(df[c_url].astype(str)  if c_url  else pd.Series([""]*len(df)))[keep]
    pdf =(df[c_pdf].astype(str)  if c_pdf  else pd.Series([""]*len(df)))[keep]

    df2=pd.DataFrame({
        "code4": code4[keep],
        "ticker": code4[keep].astype(str)+".T",
        "title": title[keep].astype(str),
        "published_at_jst": pd.to_datetime(dt[keep]),
        "body": body, "url_detail": url, "url_pdf": pdf
    })
    df2["date"]=df2["published_at_jst"].dt.normalize()

    for _,r in df2.iterrows():
        d=str(r["date"].date()); y,m,dd=d.split("-")
        outdir=DST/y/m/dd; outdir.mkdir(parents=True, exist_ok=True)
        sid=hashlib.sha1(f"{r['ticker']}|{r['published_at_jst'].strftime('%Y-%m-%d %H:%M:%S')}|{r['title']}".encode("utf-8")).hexdigest()[:16]
        out=outdir/f"{r['ticker']}_{sid}.json"
        if out.exists(): 
            continue
        rec={"ticker":r["ticker"],"code4":r["code4"],"title":r["title"],
             "published_at_jst": r["published_at_jst"].strftime("%Y-%m-%d %H:%M:%S"),
             "date": d, "event_type":"other", "source":"kabutan"}
        if str(r["body"]).strip(): rec["body"]=r["body"]
        if str(r["url_detail"]).strip(): rec["url_detail"]=r["url_detail"]
        if str(r["url_pdf"]).strip(): rec["url_pdf"]=r["url_pdf"]
        out.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
        written+=1

# サマリ
paths=list(DST.rglob("*.json"))
def ymd_of(p):
    m=re.search(r"(20\d{2})[\\/](\d{2})[\\/](\d{2})", str(p))
    return "-".join(m.groups()) if m else None
dates=sorted([ymd_of(p) for p in paths if ymd_of(p)])
by_year={}
for p in paths:
    m=re.search(r"(20\d{2})[\\/]", str(p))
    if m: by_year[m.group(1)]=by_year.get(m.group(1),0)+1
print({"json_files": len(paths), "date_min": dates[0] if dates else None, "date_max": dates[-1] if dates else None, "by_year": dict(sorted(by_year.items()))})
