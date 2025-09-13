import re,json,unicodedata as U, pandas as pd
from pathlib import Path
def N(x): 
    return U.normalize("NFKC","" if x is None or (isinstance(x,float) and pd.isna(x)) else str(x)).strip()
SRC=Path("data/bronze/tdnet")  # enrichの*.parquetが入る想定
DST=Path("data/raw/tdnet"); DST.mkdir(parents=True, exist_ok=True)
files=list(SRC.rglob("*20190910*.parquet"))  # 上の試験日
w=0
for fp in files:
    df=pd.read_parquet(fp)
    for _,r in df.iterrows():
        txt=" ".join(N(v) for v in r.values)
        m=re.search(r"(?<!\\d)(\\d{4})(?!\\d)", txt)
        if not m: continue
        code4=m.group(1); ticker=f"{code4}.T"
        # 日時
        dt=None
        for k in ["掲載日時","発表日時","開示日時","公表日時","更新日時","日時","date","datetime","published","timestamp"]:
            if k in r and N(r[k]):
                try: 
                    cand=pd.to_datetime(N(r[k]), errors="coerce")
                    if pd.notna(cand): dt=cand; break
                except: pass
        if dt is None: continue
        d=str(pd.to_datetime(dt).normalize().date()); y,mn,dd=d.split("-")
        outdir=Path("data/raw/tdnet")/y/mn/dd; outdir.mkdir(parents=True, exist_ok=True)
        title=None
        for k in ["タイトル","件名","見出し","表題","題名","開示内容","headline","subject","title","本文","内容","テキスト","body","detail","description"]:
            if k in r and len(N(r[k]))>=2: title=N(r[k]); break
        if not title: continue
        sid=f"{hash((ticker,str(dt),title)) & 0xffffffffffffffff:016x}"  # 決定的に近いID
        out=outdir/f"{ticker}_{sid}.json"
        if out.exists(): continue
        rec={"ticker":ticker,"code4":code4,"title":title,"published_at_jst":pd.to_datetime(dt).strftime("%Y-%m-%d %H:%M:%S"),"date":d,"event_type":"other","source":"kabutan"}
        out.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8"); w+=1
print({"written":w})
