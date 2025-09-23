import os, json, numpy as np, pandas as pd
EXP=os.environ["EXP_DIR"]; OOF=r"reports/checks/tdnet_model_y_2x_oof.parquet"; PRC=r"data/proc/prices/jp_prices_std_compat_q4p.parquet"
thr=0.205; H=60; Ns=[10,20]; BPS=[0.001,0.002,0.003]
o=pd.read_parquet(OOF)[["ticker","eff_date","p_raw"]]
p=pd.read_parquet(PRC, columns=["ticker","eff_date","adj_close"]).sort_values(["ticker","eff_date"])
p["next_ret"]=p.groupby("ticker")["adj_close"].pct_change().shift(-1)
g=p.groupby("ticker",group_keys=False)
ret=g["next_ret"].apply(lambda s:s.rolling(H,min_periods=H).sum()).shift(-(H-1))
ph=p.assign(ret=ret).dropna(subset=["ret"])
sig=o.merge(ph[["ticker","eff_date","ret"]],on=["ticker","eff_date"],how="inner")
sig["pick"]=(sig["p_raw"]>=thr).astype(int)
sig=sig.sort_values(["eff_date","p_raw"],ascending=[True,False])
sig["rank"]=sig.groupby("eff_date")["p_raw"].rank(method="first",ascending=False)
rows=[]
for N in Ns:
    pick=sig[(sig["pick"]==1)&(sig["rank"]<=N)]
    if pick.empty: continue
    day=pick.groupby("eff_date")["ret"].mean().values
    for c in BPS:
        day_c=day - 2*c
        ann=day_c.mean()*(252/H)
        bs=np.array([np.mean(np.random.choice(day_c,len(day_c),True)) for _ in range(1000)])*(252/H)
        rows.append({"N":N,"bps":int(c*1e4),"n":int(len(day_c)),"ann":float(ann),
                     "ci_lo":float(np.percentile(bs,2.5)),"ci_hi":float(np.percentile(bs,97.5))})
pd.DataFrame(rows).to_csv(os.path.join(EXP,"evt_cost_ci_v2.csv"), index=False)
print({"evt_cost_ci_v2":os.path.join(EXP,"evt_cost_ci_v2.csv")})
