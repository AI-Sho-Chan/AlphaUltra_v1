import pandas as pd, pathlib
fe = pd.read_parquet("tmp/features_tdnet_q4_smoke.parquet", columns=["ticker","eff_date"])
fe["ticker"]=fe["ticker"].astype(str); fe["eff_date"]=pd.to_datetime(fe["eff_date"]).dt.normalize()
tickers = fe["ticker"].unique().tolist()
px = pd.read_parquet("data/proc/prices/jp_prices_std_compat.parquet")
px.columns=[str(c) for c in px.columns]
if "adj_close" not in px.columns:
    for c in ("px_close","close","Adj Close","adjclose"):
        if c in px.columns: px["adj_close"]=px[c]; break
px["ticker"]=px["ticker"].astype(str)
px["date"]=pd.to_datetime(px.get("date", px.get("eff_date")))
px = px[(px["ticker"].isin(tickers)) & (px["date"].between("2012-01-01","2015-03-31"))].copy()
if "volume" not in px.columns: px["volume"]=0
if "addv_3m" not in px.columns: px["addv_3m"]=pd.NA
px = px.drop_duplicates(["ticker","date"])
px["eff_date"]=px["date"].dt.normalize()
out="data/proc/prices/jp_prices_std_compat_q4p.parquet"
pathlib.Path(out).parent.mkdir(parents=True, exist_ok=True)
px.to_parquet(out, index=False)
print({"out":out,"rows":len(px)})
