import pandas as pd
FE="tmp/features_tdnet_q4_smoke.parquet"
PX="data/proc/prices/jp_prices_std_compat_q4p.parquet"
need=["ret_5","ret_20","z20","mom20","v_z20"]

fe=pd.read_parquet(FE)
px=pd.read_parquet(PX,columns=["ticker","eff_date","adj_close","volume"])
fe["ticker"]=fe["ticker"].astype(str); fe["eff_date"]=pd.to_datetime(fe["eff_date"]).dt.normalize()
px["ticker"]=px["ticker"].astype(str); px["eff_date"]=pd.to_datetime(px["eff_date"]).dt.normalize()

px=px.sort_values(["ticker","eff_date"])
g=px.groupby("ticker",group_keys=False)
px["ret_5"]=g["adj_close"].pct_change(5)
px["ret_20"]=g["adj_close"].pct_change(20)
px["ma20"]=g["adj_close"].transform(lambda s:s.rolling(20,min_periods=20).mean())
px["std20"]=g["adj_close"].transform(lambda s:s.rolling(20,min_periods=20).std())
px["z20"]=(px["adj_close"]-px["ma20"])/px["std20"]
px["mom20"]=px["adj_close"]/g["adj_close"].shift(20)-1.0
px["v_ma20"]=g["volume"].transform(lambda s:s.rolling(20,min_periods=20).mean())
px["v_std20"]=g["volume"].transform(lambda s:s.rolling(20,min_periods=20).std())
px["v_z20"]=(px["volume"]-px["v_ma20"])/px["v_std20"]

# needの非欠損件数と列存在
print({"need_cols_in_px":[c in px.columns for c in need],
       "need_notna_counts":{c:int(px[c].notna().sum()) for c in need}})

pxu=px[["ticker","eff_date"]+need].dropna(subset=need)
m=fe.merge(pxu, on=["ticker","eff_date"], how="inner", validate="m:1")
print({"m_has_cols":[c in m.columns for c in need], "m_rows":len(m)})
