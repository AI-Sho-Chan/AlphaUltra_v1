import re, json, hashlib, unicodedata as ud
from pathlib import Path
import pandas as pd

SRC=Path(r"C:\AI\AlphaUltra_v1\data\raw\kabutan")
DST=Path(r"C:\AI\AlphaUltra_v1\data\raw\tdnet"); DST.mkdir(parents=True, exist_ok=True)

PRICE_KEYS={"open","high","low","close","始値","高値","安値","終値"}
CODE_KEYS   = ["コード","銘柄コード","証券コード","code","sec_code","ticker","銘柄"]
TITLE_KEYS  = ["タイトル","件名","見出し","表題","題名","開示内容","headline","subject","title"]
DT_KEYS     = ["掲載日時","発表日時","開示日時","公表日時","更新日時","日時","date","datetime","published","timestamp"]
DATE_ONLY   = ["掲載日","発表日","開示日","公表日","日付","date"]
TIME_ONLY   = ["掲載時刻","発表時刻","開示時刻","公表時刻","時刻","time"]
BODY_KEYS   = ["本文","内容","テキスト","body","detail","description"]
URL_KEYS    = ["url","詳細url","記事url","リンク","detail_url","URL","Url"]
PDF_KEYS    = ["pdf","pdf_url","PDF"]

def N(x): 
    s = "" if x is None or (isinstance(x,float) and pd.isna(x)) else str(x)
    return ud.normalize("NFKC", s).strip()

def find_col(cols, keys):
    norm = {ud.normalize("NFKC", c).lower().strip(): c for c in cols}
    for k in keys:
        k2 = ud.normalize("NFKC", k).lower().strip()
        for low,orig in norm.items():
            if k2 in low: return orig
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

def extract_code_from_sources(code_val, title_val, url_val, pdf_val):
    # 1) 明示コード列
    for txt in [code_val]:
        t=N(txt)
        if t:
            m=re.search(r"(?<!\d)(\d{4})(?!\d)", t)
            if m: return m.group(1)
    # 2) URL類
    for u in [url_val, pdf_val]:
        t=N(u).lower()
        for pat in [r"[?&](?:code|sc)=(\d{4})", r"/stock[s]?/(\d{4})", r"/(\d{4})(?:[/?#]|$)"]:
            m=re.search(pat, t)
            if m: return m.group(1)
    # 3) タイトル
    t=N(title_val)
    m=re.search(r"(?<!\d)(\d{4})(?!\d)", t)
    if m: return m.group(1)
    return None

files=[*SRC.rglob("*.csv"), *SRC.rglob("*.CSV"), *SRC.rglob("*tdnet*.tsv")]
written=0; uniq=set(); years={}
for fp in files:
    try:
        if fp.suffix.lower()==".tsv":
            df=pd.read_csv(fp, sep="\t", encoding="utf-8-sig")
        else:
            try: df=pd.read_csv(fp, encoding="utf-8-sig")
            except UnicodeDecodeError: df=pd.read_csv(fp, encoding="cp932")
    except Exception:
        continue
    low={ud.normalize("NFKC", c).lower().strip() for c in df.columns}
    if len(PRICE_KEYS & low)>=3:  # 価格表は除外
        continue

    c_code = find_col(df.columns, CODE_KEYS)
    c_title= find_col(df.columns, TITLE_KEYS)
    c_dt   = find_col(df.columns, DT_KEYS)
    c_d    = find_col(df.columns, DATE_ONLY)
    c_t    = find_col(df.columns, TIME_ONLY)
    c_body = find_col(df.columns, BODY_KEYS)
    c_url  = find_col(df.columns, URL_KEYS)
    c_pdf  = find_col(df.columns, PDF_KEYS)

    ymd = folder_ymd(fp)
    for _,row in df.iterrows():
        code4 = extract_code_from_sources(row.get(c_code), row.get(c_title), row.get(c_url), row.get(c_pdf))
        if not code4: 
            continue

        # 日時
        dt=None
        if c_dt: 
            dt=pd.to_datetime(N(row.get(c_dt)), errors="coerce")
        if (dt is None or pd.isna(dt)) and c_d:
            if c_t: dt=pd.to_datetime(N(row.get(c_d))+" "+N(row.get(c_t)), errors="coerce")
            else:   dt=pd.to_datetime(N(row.get(c_d)), errors="coerce")
        if (dt is None or pd.isna(dt)) and ymd:
            dt=pd.to_datetime(ymd+" 15:00:00")
        if dt is None or pd.isna(dt): 
            continue

        title=N(row.get(c_title)) or N(row.get(c_body))
        if not title or len(title)<2: 
            continue

        ticker=f"{code4}.T"
        d=str(pd.to_datetime(dt).normalize().date()); y,m,d2=d.split("-")
        outdir=DST/y/m/d2; outdir.mkdir(parents=True, exist_ok=True)
        sid=hashlib.sha1(f"{ticker}|{pd.to_datetime(dt).strftime('%Y-%m-%d %H:%M:%S')}|{title}".encode("utf-8")).hexdigest()[:16]
        out=outdir/f"{ticker}_{sid}.json"
        if out.exists(): 
            continue

        rec={"ticker":ticker,"code4":code4,"title":title,
             "published_at_jst": pd.to_datetime(dt).strftime("%Y-%m-%d %H:%M:%S"),
             "date": d, "event_type":"other","source":"kabutan"}
        u=N(row.get(c_url)); p=N(row.get(c_pdf)); b=N(row.get(c_body))
        if u: rec["url_detail"]=u
        if p: rec["url_pdf"]=p
        if b: rec["body"]=b

        out.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
        written+=1; uniq.add(ticker); years[y]=years.get(y,0)+1

# サマリ
paths=list(DST.rglob("*.json"))
def ymd_of(p):
    m=re.search(r"(20\d{2})[\\/](\d{2})[\\/](\d{2})", str(p))
    return "-".join(m.groups()) if m else None
dates=sorted([ymd_of(p) for p in paths if ymd_of(p)])
print({"json_files": len(paths), "tickers": len(uniq),
       "date_min": dates[0] if dates else None, "date_max": dates[-1] if dates else None,
       "by_year": dict(sorted(years.items()))})
