import pandas as pd
fe = pd.read_parquet("data/proc/features_tdnet/tdnet_event_features.parquet", columns=["ticker","eff_date"]).dropna()
px = pd.read_parquet("data/proc/prices/jp_prices_std_compat_slim_q4.parquet", columns=["ticker","eff_date"]).dropna()
fe["eff_date"]=pd.to_datetime(fe["eff_date"]).dt.normalize()
px["eff_date"]=pd.to_datetime(px["eff_date"]).dt.normalize()
print({
 "fe_keys": len(fe.drop_duplicates()),
 "px_keys": len(px.drop_duplicates()),
 "intersect": len(fe.merge(px, on=["ticker","eff_date"], how="inner").drop_duplicates())
})
