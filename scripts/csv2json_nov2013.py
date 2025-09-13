import re, json
from pathlib import Path
import pandas as pd
SRC=Path(r"C:\AI\AlphaUltra\data\raw\kabutan")           # 旧の在庫を使用
DST=Path(r"C:\AI\AlphaUltra_v1\data\raw\tdnet"); DST.mkdir(parents=True, exist_ok=True)
def ymd_from(p):
    m=re.search(r"(20\d{2})-(\d{2})-(\d{2})", str(p))
    return "-".join(m.groups()) if m else None
for d in [f"2013-11-{i:02d}" for i in range(10,21)]:
    fp=SRC/f"{d}/tdnet.csv"
    if not fp.exists(): continue
    try:
        df=pd.read_csv(fp,encoding="utf-8-sig")
    except UnicodeDecodeError:
        df=pd.read_csv(fp,encoding="cp932")
    cols={c:"コード" for c in df.columns if "コード" in c or "code"==c.lower()}
    code_col = next(iter(cols), None)
    dt_col   = next((c for c in df.columns if any(k in c for k in ["掲載日時","日時","date","time"])), None)
    title_col= next((c for c in df.columns if any(k in c for k in ["タイトル","title","件名"])), None)
    if not(code_col and title_col): continue
    dt = pd.to_datetime(df[dt_col], errors="coerce") if dt_col else None
    for i,r in df.iterrows():
        m=re.search(r"(?<!\d)(\d{4})(?!\d)", str(r[code_col])); 
        if not m: continue
        code=m.group(1); ticker=f"{code}.T"
        title=str(r[title_col]).strip()
        if not title: continue
        dstr = ymd_from(fp) or (str(dt.iloc[i].date()) if dt is not None and pd.notna(dt.iloc[i]) else d)
        y,mn,dd=dstr.split("-")
        outdir=DST/y/mn/dd; outdir.mkdir(parents=True, exist_ok=True)
        rec={"ticker":ticker,"code4":code,"title":title,
             "published_at_jst": (str(dt.iloc[i]) if dt is not None and pd.notna(dt.iloc[i]) else f"{dstr} 15:00:00"),
             "date":dstr,"event_type":"other","source":"kabutan"}
        (outdir/f"{ticker}_{i:06d}.json").write_text(json.dumps(rec,ensure_ascii=False),encoding="utf-8")
print("done")
