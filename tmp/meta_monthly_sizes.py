import os, json, numpy as np, pandas as pd
EXP=r"reports\exp\20250923_202008"; H=20
m=pd.read_parquet(r"reports/checks/meta_y_2x_oof.parquet")[["ticker","eff_date","p_raw"]]
p=pd.read_parquet(r"data/proc/prices/jp_prices_std_compat_q4p.parquet",
                  columns=["ticker","eff_date","adj_close"]).sort_values(["ticker","eff_date"])
p["next_ret"]=p.groupby("ticker")["adj_close"].pct_change().shift(-1)
g=p.groupby("ticker",group_keys=False)
ret=g["next_ret"].apply(lambda s:s.rolling(H,min_periods=H).sum()).shift(-(H-1))
ph=p.assign(ret=ret).dropna(subset=["ret"])
rank=m.merge(ph[["ticker","eff_date","ret"]],on=["ticker","eff_date"],how="inner") \
       .sort_values(["eff_date","p_raw"],ascending=[True,False])
rank["r"]=rank.groupby("eff_date")["p_raw"].rank(method="first",ascending=False)
rows=[]
for K in (5,10):
    day=rank[rank["r"]<=K].groupby("eff_date")["ret"].mean()
    mret=day.resample("ME").mean(); ann=float(mret.mean()*12) if len(mret)>0 else 0.0
    rows.append({"rule":f"TOP{K}","months":int(len(mret)),"ann":ann})
pd.DataFrame(rows).to_csv(os.path.join(EXP,"meta_monthly_sizes.csv"), index=False)
print({"meta_monthly_sizes":os.path.join(EXP,"meta_monthly_sizes.csv")})
