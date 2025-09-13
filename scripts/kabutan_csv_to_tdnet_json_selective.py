import re, json, hashlib, unicodedata as U, pandas as pd
from pathlib import Path
def N(x): 
    if x is None or (isinstance(x,float) and pd.isna(x)): return ""
    return U.normalize("NFKC", str(x)).strip()

SRC = Path(r"C:\AI\AlphaUltra_v1\data\raw\kabutan")
DST = Path(r"C:\AI\AlphaUltra_v1\data\raw\tdnet"); DST.mkdir(parents=True, exist_ok=True)
RMIN, RMAX = "2013-09-01", "2024-09-10"

CODE_COLS  = ["コード","銘柄コード","証券コード","code","sec_code"]
TITLE_COLS = ["タイトル","件名","見出し","表題","題名","開示内容","headline","subject","title"]
DT_COLS    = ["掲載日時","発表日時","開示日時","公表日時","更新日時","日時","date","datetime","published","timestamp"]
DATE_COLS  = ["掲載日","発表日","開示日","公表日","日付","date"]
TIME_COLS  = ["掲載時刻","発表時刻","開示時刻","公表時刻","時刻","time"]

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

def pick(cols, cand):
    nm = {U.normalize("NFKC",c).lower(): c for c in cols}
    for k in cand:
        kk=U.normalize("NFKC",k).lower()
        for low,orig in nm.items():
            if kk in low: return orig
    return None

files = list(SRC.rglob("*.csv")) + list(SRC.rglob("*.CSV")) + list(SRC.rglob("*tdnet*.tsv"))
w=0; tick=set(); by_year={}
for fp in files:
    ymd = folder_ymd(fp)
    if not ymd or not (RMIN <= ymd <= RMAX): 
        continue
    # 読み込み
    try:
        if fp.suffix.lower()==".tsv":
            df=pd.read_csv(fp, sep="\t", encoding="utf-8-sig")
        else:
            try: df=pd.read_csv(fp, encoding="utf-8-sig")
            except UnicodeDecodeError: df=pd.read_csv(fp, encoding="cp932")
    except Exception:
        continue

    c_code = pick(df.columns, CODE_COLS)
    if not c_code:  # コード列が無いCSVはスキップ
        continue
    c_title= pick(df.columns, TITLE_COLS)
    c_dt   = pick(df.columns, DT_COLS)
    c_d    = pick(df.columns, DATE_COLS)
    c_t    = pick(df.columns, TIME_COLS)

    for _,r in df.iterrows():
        # コード列からのみ4桁抽出（行全体スキャンはしない＝年の誤抽出を遮断）
        m=re.search(r"(?<!\d)(\d{4})(?!\d)", N(r.get(c_code)))
        if not m: 
            continue
        code4=m.group(1); ticker=f"{code4}.T"

        # タイトル
        title=None
        if c_title: 
            t=N(r.get(c_title))
            if len(t)>=2: title=t
        if not title: 
            continue

        # 日時
        dt=None
        if c_dt:
            dt=pd.to_datetime(N(r.get(c_dt)), errors="coerce")
        if (dt is None or pd.isna(dt)) and c_d:
            if c_t: dt=pd.to_datetime(N(r.get(c_d))+" "+N(r.get(c_t)), errors="coerce")
            else:   dt=pd.to_datetime(N(r.get(c_d)), errors="coerce")
        if pd.isna(dt) or dt is None:
            dt=pd.to_datetime(ymd+" 15:00:00")

        d=str(pd.to_datetime(dt).normalize().date()); y,m,dd=d.split("-")
        outdir=DST/y/m/dd; outdir.mkdir(parents=True, exist_ok=True)
        sid=hashlib.sha1(f"{ticker}|{dt.strftime('%Y-%m-%d %H:%M:%S')}|{title}".encode("utf-8")).hexdigest()[:16]
        out=outdir/f"{ticker}_{sid}.json"
        if out.exists(): 
            continue
        rec={"ticker":ticker,"code4":code4,"title":title,
             "published_at_jst":dt.strftime("%Y-%m-%d %H:%M:%S"),
             "date": d, "event_type":"other","source":"kabutan"}
        out.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
        w+=1; tick.add(ticker); by_year[y]=by_year.get(y,0)+1

# サマリ
paths=list(DST.rglob("*.json"))
def ymd_of(p):
    m=re.search(r"(20\d{2})[\\/](\d{2})[\\/](\d{2})", str(p))
    return "-".join(m.groups()) if m else None
dates=sorted([ymd_of(p) for p in paths if ymd_of(p)])
print({"json_files": len(paths), "tickers": len(tick),
       "date_min": dates[0] if dates else None, "date_max": dates[-1] if dates else None,
       "by_year": dict(sorted(by_year.items()))})
