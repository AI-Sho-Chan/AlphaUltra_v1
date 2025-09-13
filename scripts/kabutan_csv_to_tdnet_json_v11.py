import re, json, hashlib, unicodedata as U, pandas as pd
from pathlib import Path
def N(x): 
    if x is None or (isinstance(x,float) and pd.isna(x)): return ""
    return U.normalize("NFKC", str(x)).strip()

SRC=Path(r"C:\AI\AlphaUltra_v1\data\raw\kabutan")
DST=Path(r"C:\AI\AlphaUltra_v1\data\raw\tdnet_new"); DST.mkdir(parents=True, exist_ok=True)
RMIN,RMAX="2019-09-01","2019-09-30"

CODE_COLS=["コード","銘柄コード","証券コード","code","sec_code"]
TITLE_COLS=["タイトル","件名","見出し","表題","題名","headline","subject","title","title_html","text_snippet"]
DT_COLS=["掲載日時","発表日時","開示日時","公表日時","更新日時","日時","date","datetime","published","timestamp"]
DATE_COLS=["掲載日","発表日","開示日","公表日","日付","date"]
TIME_COLS=["掲載時刻","発表時刻","開示時刻","公表時刻","時刻","time"]
URL_COLS=["URL","url","detail_url","リンク","記事url","詳細url","pdf","PDF","添付URL"]

def folder_ymd(p:Path):
    s=str(p)
    m=re.search(r"(20\d{2})[-_/](\d{2})[-_/](\d{2})", s)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None

def pick(cols,cand):
    nm={U.normalize("NFKC",c).lower():c for c in cols}
    for k in cand:
        kk=U.normalize("NFKC",k).lower()
        for low,orig in nm.items():
            if kk in low: return orig
    return None

def read_flex(fp:Path):
    for enc in ("utf-8-sig","cp932"):
        for sep,eng in ((None,"python"),(",",None),("\t",None),(";",None),("|",None)):
            try:
                kw={"encoding":enc}
                if sep is None: kw.update(sep=None, engine=eng)
                else: kw.update(sep=sep)
                return pd.read_csv(fp, **kw)
            except Exception:
                continue
    return None

files=[*SRC.rglob("*.csv"),*SRC.rglob("*.CSV"),*SRC.rglob("*tdnet*.tsv")]
w=0; uniq=set(); byy={}
for fp in files:
    ymd=folder_ymd(fp)
    if not ymd or not (RMIN<=ymd<=RMAX): 
        continue
    df=read_flex(fp)
    if df is None or df.empty: 
        continue

    c_code=pick(df.columns,CODE_COLS)
    c_title=pick(df.columns,TITLE_COLS)
    c_dt=pick(df.columns,DT_COLS); c_d=pick(df.columns,DATE_COLS); c_t=pick(df.columns,TIME_COLS)
    url_cands=[c for c in URL_COLS if pick(df.columns,[c])]

    for _,r in df.iterrows():
        code4=None
        # 1) コード列
        if c_code:
            m=re.search(r"(?<!\d)(\d{4})(?!\d)", N(r.get(c_code))); 
            if m: code4=m.group(1)
        # 2) URL列（?code=XXXX or /code/XXXX）
        if not code4 and url_cands:
            blob=" ".join(N(r.get(pick(df.columns,[c]))) for c in URL_COLS if pick(df.columns,[c]))
            m=re.search(r"[?&]code=(\d{4})", blob) or re.search(r"/code/(\d{4})", blob) or re.search(r"(?<!\d)(\d{4})(?!\d)", blob)
            if m: code4=m.group(1)
        if not code4 or not code4.isdigit() or not (1300<=int(code4)<=9999):
            continue
        ticker=f"{code4}.T"

        title=N(r.get(c_title)) if c_title else ""
        if len(title)<2: 
            continue

        dt=None
        if c_dt: dt=pd.to_datetime(N(r.get(c_dt)), errors="coerce")
        if (dt is None or pd.isna(dt)) and c_d:
            if c_t: dt=pd.to_datetime(N(r.get(c_d))+" "+N(r.get(c_t)), errors="coerce")
            else:   dt=pd.to_datetime(N(r.get(c_d)), errors="coerce")
        if dt is None or pd.isna(dt): dt=pd.to_datetime(ymd+" 15:00:00")

        d=str(pd.to_datetime(dt).normalize().date()); y,m,dd=d.split("-")
        outdir=DST/y/m/dd; outdir.mkdir(parents=True, exist_ok=True)
        sid=hashlib.sha1(f"{ticker}|{dt.strftime('%Y-%m-%d %H:%M:%S')}|{title}".encode("utf-8")).hexdigest()[:16]
        out=outdir/f"{ticker}_{sid}.json"
        if out.exists(): 
            continue
        rec={"ticker":ticker,"code4":code4,"title":title,
             "published_at_jst":dt.strftime("%Y-%m-%d %H:%M:%S"),
             "date":d,"event_type":"other","source":"kabutan"}
        out.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
        w+=1; uniq.add(ticker); byy[y]=byy.get(y,0)+1

paths=list(DST.rglob("*.json"))
def ymd_of(p):
    m=re.search(r"(20\d{2})[\\/](\d{2})[\\/](\d{2})", str(p))
    return "-".join(m.groups()) if m else None
dates=sorted([ymd_of(p) for p in paths if ymd_of(p)])
print({"json_files":len(paths),"tickers":len(uniq),
       "date_min":dates[0] if dates else None,"date_max":dates[-1] if dates else None,
       "by_year":dict(sorted(byy.items()))})
