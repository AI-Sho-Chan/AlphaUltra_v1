import pandas as pd, pathlib
FE="tmp/features_tdnet_q4_smoke.parquet"
PX="data/proc/prices/jp_prices_std_compat_q4p.parquet"
need=["ret_5","ret_20","z20","mom20","v_z20"]

fe=pd.read_parquet(FE)
px=pd.read_parquet(PX,columns=["ticker","eff_date","adj_close","volume"])
fe["ticker"]=fe["ticker"].astype(str); fe["eff_date"]=pd.to_datetime(fe["eff_date"]).dt.normalize()
px["ticker"]=px["ticker"].astype(str); px["eff_date"]=pd.to_datetime(px["eff_date"]).dt.normalize()

px=px.sort_values(["ticker","eff_date"]); g=px.groupby("ticker",group_keys=False)

def build(minp):
    p=px.copy()
    p["ret_5"]=g["adj_close"].pct_change(5)
    p["ret_20"]=g["adj_close"].pct_change(20)
    p["ma20"]=g["adj_close"].transform(lambda s:s.rolling(20,min_periods=minp).mean())
    p["std20"]=g["adj_close"].transform(lambda s:s.rolling(20,min_periods=minp).std())
    p["z20"]=(p["adj_close"]-p["ma20"])/p["std20"]
    p["mom20"]=p["adj_close"]/g["adj_close"].shift(20)-1.0
    p["v_ma20"]=g["volume"].transform(lambda s:s.rolling(20,min_periods=minp).mean())
    p["v_std20"]=g["volume"].transform(lambda s:s.rolling(20,min_periods=minp).std())
    p["v_z20"]=(p["volume"]-p["v_ma20"])/p["v_std20"]
    pxu=p[["ticker","eff_date"]+need].dropna(subset=need).drop_duplicates(["ticker","eff_date"])
    m=fe.merge(pxu,on=["ticker","eff_date"],how="inner",validate="m:1")
    return m

m=build(20)
if len(m)==0 or any(m[c].std()==0 for c in need): m=build(10)
for c in need: m[c]=pd.to_numeric(m[c],errors="coerce").astype("float32")
m.to_parquet("tmp/features_tdnet_q4_smoke.parquet",index=False)
print({"rows":len(m),"zero_var":int((m[need].std()==0).sum())})
