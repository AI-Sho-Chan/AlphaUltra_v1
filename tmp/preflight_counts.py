import pandas as pd
f="tmp/features_tdnet_q4_intersect.parquet"
p="data/proc/prices/jp_prices_std_compat_slim_q4.parquet"
fe=pd.read_parquet(f, columns=["ticker","eff_date"])
px=pd.read_parquet(p, columns=["ticker","eff_date"])
print({"fe_rows":len(fe),"fe_keys":len(fe.drop_duplicates()),
       "px_rows":len(px),"px_keys":len(px.drop_duplicates())})
