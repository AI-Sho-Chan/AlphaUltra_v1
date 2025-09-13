import pandas as pd, json
f="data/proc/features_tdnet/tdnet_event_features.parquet"
p="data/proc/prices/jp_prices_std.parquet"
df=pd.read_parquet(f,columns=["ticker","date"])
df["date"]=pd.to_datetime(df["date"])
df=df[(df["date"]>="2025-06-01")&(df["date"]<="2025-08-31")]
t_feat=sorted(set(df["ticker"].astype(str)))
px=pd.read_parquet(p,columns=["ticker"])
t_px=sorted(set(px["ticker"].astype(str)))
t_int=sorted(set(t_feat)&set(t_px))
print(json.dumps({"features_2025_tickers":len(t_feat),
                  "prices_tickers":len(t_px),
                  "intersection":len(t_int),
                  "sample":t_int[:10]},ensure_ascii=False))
