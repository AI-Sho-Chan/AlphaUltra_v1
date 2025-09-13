import re, json, hashlib
from pathlib import Path
import pandas as pd

SRC=Path(r"C:\AI\AlphaUltra_v1\data\raw\kabutan")
DST=Path(r"C:\AI\AlphaUltra_v1\data\raw\tdnet"); DST.mkdir(parents=True, exist_ok=True)

PRICE_KEYS={"open","high","low","close","始値","高値","安値","終値"}  # 価格表除外
# 列シノニム
CODE_KEYS   = ["コード","銘柄コード","証券コード","コード番号","code","sec_code","ticker","銘柄"]
TITLE_KEYS  = ["タイトル","件名","見出し","表題","題名","開示内容","概要","headline","subject","title"]
DT_KEYS     = ["掲載日時","発表日時","開示日時","公表日時","更新日時","日時","date","datetime","published","timestamp"]
DATE_ONLY   = ["掲載日","発表日","開示日","公表日","日付","date"]
TIME_ONLY   = ["掲載時刻","発表時刻","開示時刻","公表時刻","時刻","time"]
BODY_KEYS   = ["本文","内容","テキスト","body","detail","description"]
URL_KEYS    = ["url","詳細url","記事url","リンク","detail_url"]
PDF_KEYS    = ["pdf","pdf_url"]

def find_col(cols, keys):
    m={c.lower().strip():c for c in cols}
    for k in keys:
        for low,orig in m.items():
            if k in low: return orig
    return None

def folder_ymd(p:Path):
    s=str(p)
    m=re.search(r"(20\d{2})[-_/](\d{2})[-_/](\d{2})", s)
    if m: return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    parts=p.parts
    for i in range(len(parts)-2):
        if re.fullmatch(r"20\d{2}", parts[i]) and re.fullmatch(r"\d{2}", parts[i+1]) and re.fullmatch(r"\d{2}", parts[i+2]):
            return f"{parts[i]}-{parts[i+1]}-{parts[i+2]}"
    m=re.search(r"(20\d{2})(\d{2})(\d{2})", s)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None

def row_code(series):
    # どの列からでも4桁コード抽出
    for v in series:
        m=re.search(r"\b(\d{4})\b", str(v))
        if m: return m.group(1)
    return None

def row_title(df_row, c_title):
    if c_title: 
        t=str(df_row[c_title])
        if t and t!='nan': return t
    # 次善：本文や概要の長文
    for k in BODY_KEYS+["概要","見出し"]:
        if k in df_row.index:
            s=str(df_row[k])
            if s and s!='nan' and len(s)>=4: return s
    # 最後：最長テキスト
    texts=[str(v) for v in df_row.values if isinstance(v,str) and len(str(v))>=4]
    return max(texts, key=len) if texts else None

files=[*SRC.rglob("*.csv"), *SRC.rglob("*.CSV"), *SRC.rglob("*tdnet*.tsv")]
w=0
for fp in files:
    # CSV読込
    try:
        if fp.suffix.lower()==".tsv":
            df=pd.read_csv(fp, sep="\t", encoding="utf-8-sig")
        else:
            try: df=pd.read_csv(fp, encoding="utf-8-sig")
            except UnicodeDecodeError: df=pd.read_csv(fp, encoding="cp932")
    except Exception:
        continue

    # 価格表除外
    low={c.lower() for c in df.columns}
    if len(PRICE_KEYS & low)>=3:
        continue

    # 列検出
    c_code  = find_col(df.columns, CODE_KEYS)
    c_title = find_col(df.columns, TITLE_KEYS)
    c_dt    = find_col(df.columns, DT_KEYS)
    c_d     = find_col(df.columns, DATE_ONLY)
    c_t     = find_col(df.columns, TIME_ONLY)
    c_body  = find_col(df.columns, BODY_KEYS)
    c_url   = find_col(df.columns, URL_KEYS)
    c_pdf   = find_col(df.columns, PDF_KEYS)

    # 行ごとに抽出
    ymd = folder_ymd(fp)
    for _,row in df.iterrows():
        code4=None
        if c_code:
            code4 = re.search(r"\b(\d{4})\b", str(row[c_code])); code4 = code4.group(1) if code4 else None
        if not code4:
            code4 = row_code(row)  # 全列走査
        if not code4: 
            continue

        # 日時
        dt=None
        if c_dt:
            dt=pd.to_datetime(row[c_dt], errors="coerce")
        if (dt is None or pd.isna(dt)) and c_d:
            if c_t:
                dt=pd.to_datetime(f"{row[c_d]} {row[c_t]}", errors="coerce")
            else:
                dt=pd.to_datetime(row[c_d], errors="coerce")
        if (dt is None or pd.isna(dt)) and ymd:
            dt=pd.to_datetime(ymd+" 15:00:00")  # 保守的
        if dt is None or pd.isna(dt):
            continue

        # タイトル
        title=row_title(row, c_title)
        if not title: 
            continue

        ticker=f"{code4}.T"
        d=str(pd.to_datetime(dt).normalize().date())
        y,m,d2=d.split("-")
        outdir=DST/y/m/d2; outdir.mkdir(parents=True, exist_ok=True)

        sid=hashlib.sha1(f"{ticker}|{pd.to_datetime(dt).strftime('%Y-%m-%d %H:%M:%S')}|{title}".encode("utf-8")).hexdigest()[:16]
        out=outdir/f"{ticker}_{sid}.json"
        if out.exists(): 
            continue

        rec={"ticker":ticker,"code4":code4,"title":str(title),
             "published_at_jst": pd.to_datetime(dt).strftime("%Y-%m-%d %H:%M:%S"),
             "date": d, "event_type":"other","source":"kabutan"}
        if c_body: 
            bv=str(row[c_body])
            if bv and bv!='nan': rec["body"]=bv
        if c_url:
            uv=str(row[c_url])
            if uv and uv!='nan': rec["url_detail"]=uv
        if c_pdf:
            pv=str(row[c_pdf])
            if pv and pv!='nan': rec["url_pdf"]=pv

        out.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
        w+=1

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
