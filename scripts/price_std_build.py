import re, pandas as pd
from pathlib import Path

SRC = Path("data/raw/prices")
OUT = Path("data/proc/prices"); OUT.mkdir(parents=True, exist_ok=True)

frames=[]
for fp in SRC.rglob("*.parquet"):
    try:
        d = pd.read_parquet(fp)
    except Exception:
        continue
    cols = {c.lower(): c for c in d.columns}
    # 日付
    if "date" in cols: dt = pd.to_datetime(d[cols["date"]])
    elif d.index.name and d.index.dtype.kind in "Mm": 
        dt = pd.to_datetime(d.index)
    else:
        continue
    # ティッカー
    if "ticker" in cols: tk = d[cols["ticker"]].astype(str)
    elif "symbol" in cols: tk = d[cols["symbol"]].astype(str)
    else:
        m = re.search(r"(\d{4}\.T)", fp.name)
        if not m: continue
        tk = pd.Series([m.group(1)]*len(d))
    # 終値（調整が無ければ Close を採用）
    ac=None
    for k in ["adj_close","adj close","adjusted close","adjusted_close"]: 
        if k in cols: ac = pd.to_numeric(d[cols[k]], errors="coerce"); break
    if ac is None:
        for k in ["close","Close","終値","c"]:
            if k.lower() in cols: ac = pd.to_numeric(d[cols[k.lower()]], errors="coerce"); break
    if ac is None: 
        continue
    # 出来高
    vol=None
    for k in ["volume","Volume","出来高","v"]:
        if k.lower() in cols: vol = pd.to_numeric(d[cols[k.lower()]], errors="coerce"); break

    frames.append(pd.DataFrame({
        "date": pd.to_datetime(dt).dt.normalize(),
        "ticker": tk,
        "adj_close": ac,
        "volume": vol
    }))

if not frames:
    print({"rows":0}); raise SystemExit

px = (pd.concat(frames, ignore_index=True)
        .dropna(subset=["date","ticker","adj_close"])
        .sort_values(["ticker","date"])
        .drop_duplicates(["ticker","date"]))
px.to_parquet(OUT/"jp_prices_std.parquet", index=False)
print({"rows": int(len(px)), "tickers": int(px["ticker"].nunique()),
       "date_min": str(px["date"].min().date()), "date_max": str(px["date"].max().date())})
