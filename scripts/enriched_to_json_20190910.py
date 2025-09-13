import re,json,unicodedata as U,pandas as pd
from pathlib import Path
def N(x): return U.normalize("NFKC","" if x is None or (isinstance(x,float) and pd.isna(x)) else str(x)).strip()
SRC=Path(r"C:\AI\AlphaUltra\data\bronze\tdnet\tdnet_day_with_html_20190910.parquet")
DST=Path(r"C:\AI\AlphaUltra_v1\data\raw\tdnet"); DST.mkdir(parents=True, exist_ok=True)
df=pd.read_parquet(SRC)
w=0
for _,r in df.iterrows():
    txt=" ".join(N(v) for v in r.values)
    m=re.search(r"(?<!\d)(\d{4})(?!\d)", txt)
    if not m: continue
    code4=m.group(1); ticker=f"{code4}.T"
    # 日時
    dt=None
    for k in ["掲載日時","発表日時","開示日時","公表日時","更新日時","日時","date","datetime","published","timestamp"]:
        if k in r and N(r[k]):
            cand=pd.to_datetime(N(r[k]), errors='coerce')
            if pd.notna(cand): dt=cand; break
    if dt is None: continue
    d=str(pd.to_datetime(dt).normalize().date()); y,mn,dd=d.split("-")
    outdir=Path(r"C:\AI\AlphaUltra_v1\data\raw\tdnet")/y/mn/dd; outdir.mkdir(parents=True, exist_ok=True)
    # タイトル
    title=None
    for k in ["タイトル","件名","見出し","表題","題名","開示内容","headline","subject","title","本文","内容","テキスト","body","detail","description"]:
        if k in r and len(N(r[k]))>=2: title=N(r[k]); break
    if not title: continue
    sid=f"{abs(hash((ticker,str(dt),title)))%10**16:016d}"
    (outdir/f"{ticker}_{sid}.json").write_text(json.dumps(
        {"ticker":ticker,"code4":code4,"title":title,"published_at_jst":pd.to_datetime(dt).strftime('%Y-%m-%d %H:%M:%S'),"date":d,"event_type":"other","source":"kabutan"},
        ensure_ascii=False), encoding='utf-8')
    w+=1
print({'written':w})
