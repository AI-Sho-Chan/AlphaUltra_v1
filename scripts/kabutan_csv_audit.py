import json, re
from pathlib import Path
import pandas as pd

root = Path(r"C:\AI\AlphaUltra_v1\data\raw\kabutan")
price_keys = {"open","high","low","close","始値","高値","安値","終値"}
dt_keys = ["掲載日時","発表日時","公表日時","日時","date","datetime","time","published"]
need_cols = [["コード","銘柄コード","code"], ["タイトル","件名","title","表題"]]

def pick(cols, keys):
    m={c.lower():c for c in cols}
    for k in keys:
        for low,orig in m.items():
            if k in low: return orig
    return None

stats = {"files":0,"price_like":0,"has_dtcol":0,"tdnet_like":0,"by_year":{}}
for fp in root.rglob("*.csv"):
    try:
        try: df = pd.read_csv(fp, nrows=0, encoding="utf-8-sig")
        except: df = pd.read_csv(fp, nrows=0, encoding="cp932")
    except: 
        continue
    cols = list(df.columns)
    low = {c.lower() for c in cols}
    stats["files"] += 1
    if len(price_keys & low) >= 3:
        stats["price_like"] += 1
        cat = "price"
    else:
        has_dt = any(any(k in c.lower() for k in dt_keys) for c in cols)
        has_code = pick(cols, need_cols[0]) is not None
        has_title= pick(cols, need_cols[1]) is not None
        if has_dt: stats["has_dtcol"] += 1
        if has_code and has_title and has_dt:
            stats["tdnet_like"] += 1
        cat = "tdnet" if has_code and has_title else "other"
    m = re.search(r"(20\d{2})", str(fp))
    if m:
        y = m.group(1); stats["by_year"][y] = stats["by_year"].get(y,0)+1

print(json.dumps(stats, ensure_ascii=False))
