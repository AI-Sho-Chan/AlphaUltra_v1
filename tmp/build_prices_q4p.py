import pathlib, pandas as pd, json, numpy as np
chosen = "data/proc/prices/jp_prices_std_compat.parquet"  # 元のフル価格
features = pathlib.Path("tmp/features_tdnet_q4_intersect_unique.parquet")
fe = pd.read_parquet(features, columns=["ticker","eff_date"])
fe["eff_date"]=pd.to_datetime(fe["eff_date"]).dt.normalize()
tickers = fe["ticker"].astype(str).unique().tolist()
win_lo = pd.Timestamp("2013-11-01")
win_hi = pd.Timestamp("2015-03-31")  # ← 将来バッファ

px = pd.read_parquet(chosen)
px.columns = [str(c) for c in px.columns]
if "adj_close" not in px.columns:
    for c in ("px_close","close","Adj Close","adjclose"):
        if c in px.columns: px["adj_close"]=px[c]; break
px["date"] = pd.to_datetime(px.get("date", px.get("Date")))
px = px[px["date"].between(win_lo, win_hi)]
if tickers: px = px[px["ticker"].astype(str).isin(tickers)]
if "volume" not in px.columns: px["volume"]=0
if "addv_3m" not in px.columns: px["addv_3m"]=pd.NA
px = px.drop_duplicates(["ticker","date"]).copy()
px["eff_date"]=px["date"]
px.to_parquet("data/proc/prices/jp_prices_std_compat_q4p.parquet", index=False)
print({"out":"data/proc/prices/jp_prices_std_compat_q4p.parquet","rows":len(px)})
