import pandas as pd, numpy as np
FE="tmp/features_tdnet_q4_work.parquet"; PX="data/proc/prices/jp_prices_std_compat_q4p.parquet"
fe=pd.read_parquet(FE, columns=["ticker","eff_date","y_2x"])
fe["ticker"]=fe["ticker"].astype(str); fe["eff_date"]=pd.to_datetime(fe["eff_date"]).dt.normalize()
px=pd.read_parquet(PX, columns=["ticker","eff_date","adj_close","volume"])
px["ticker"]=px["ticker"].astype(str); px["eff_date"]=pd.to_datetime(px["eff_date"]).dt.normalize()
px=px.sort_values(["ticker","eff_date"])
g=px.groupby("ticker",group_keys=False)
px["mom63"]=px["adj_close"]/g["adj_close"].shift(63)-1.0
px["vol20"]=g["adj_close"].transform(lambda s:s.pct_change().rolling(20,min_periods=20).std())
px["v_lq"]=g["volume"].transform(lambda s:s.rolling(20,min_periods=20).mean())
pxu=px[["ticker","eff_date","mom63","vol20","v_lq"]].dropna().drop_duplicates(["ticker","eff_date"])
fnd=fe.merge(pxu,on=["ticker","eff_date"],how="inner",validate="m:1").reset_index(drop=True)
fnd.to_parquet("tmp/features_fnd_2600.parquet", index=False)
print({"rows":len(fnd),"nfeat":3})
