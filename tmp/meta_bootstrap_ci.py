import os, json, numpy as np, pandas as pd
from scipy import stats
EXP=os.environ["EXP_DIR"]; OOF=r"reports/checks/meta_y_2x_oof.parquet"; PRC=r"data/proc/prices/jp_prices_std_compat_q4p.parquet"
thr=0.355; H=20; B=1000
m=pd.read_parquet(OOF)[["ticker","eff_date","p_raw"]]
p=pd.read_parquet(PRC, columns=["ticker","eff_date","adj_close"]).sort_values(["ticker","eff_date"])
p["next_ret"]=p.groupby("ticker")["adj_close"].pct_change().shift(-1)
g=p.groupby("ticker",group_keys=False)
ret=g["next_ret"].apply(lambda s:s.rolling(H,min_periods=H).sum()).shift(-(H-1))
ph=p.assign(ret=ret).dropna(subset=["ret"])
sig=m.merge(ph[["ticker","eff_date","ret"]],on=["ticker","eff_date"],how="inner")
sig=sig[sig["p_raw"]>=thr]
day=sig.groupby("eff_date")["ret"].mean().values
if len(day)<5:
    out={"n":int(len(day)),"ann":0,"p":1.0,"ci":[0,0]}
else:
    ann=day.mean()*(252/H)
    bs=np.array([np.mean(np.random.choice(day,size=len(day),replace=True)) for _ in range(B)])*(252/H)
    ci=[float(np.percentile(bs,2.5)), float(np.percentile(bs,97.5))]
    pval=float(stats.ttest_1samp(day,0.0,alternative="greater").pvalue)
    out={"n":int(len(day)),"ann":float(ann),"p":pval,"ci":ci}
with open(os.path.join(EXP,"meta_ci.json"),"w",encoding="utf-8") as f: json.dump(out,f,ensure_ascii=False,indent=2)
print({"meta_ci":os.path.join(EXP,"meta_ci.json")})
