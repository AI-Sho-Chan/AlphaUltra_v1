import os, json, pandas as pd, numpy as np
from scipy import stats
EXP = os.environ["EXP_DIR"]
m = pd.read_parquet(r"reports/checks/meta_y_2x_oof.parquet")[["ticker","eff_date","p_raw"]]
p = pd.read_parquet(r"data/proc/prices/jp_prices_std_compat_q4p.parquet", columns=["ticker","eff_date","adj_close"]).sort_values(["ticker","eff_date"])
p["next_ret"]=p.groupby("ticker")["adj_close"].pct_change().shift(-1)
H, thr = 20, 0.355
g=p.groupby("ticker",group_keys=False)
ret=g["next_ret"].apply(lambda s:s.rolling(H,min_periods=H).sum()).shift(-(H-1))
ph=p.assign(ret=ret).dropna(subset=["ret"])
sig=m.merge(ph[["ticker","eff_date","ret"]],on=["ticker","eff_date"],how="inner")
sig=sig[sig["p_raw"]>=thr]
day=sig.groupby("eff_date")["ret"].mean()
ann_excess=float(day.mean()*(252/H)); pval=float(stats.ttest_1samp(day,0.0,alternative="greater").pvalue) if len(day)>2 else 1.0
out={"H":H,"thr":thr,"ann_excess":ann_excess,"t_p":pval,"coverage":float(len(sig)/len(m))}
with open(os.path.join(EXP,"meta_summary.json"),"w",encoding="utf-8") as f: json.dump(out,f,ensure_ascii=False,indent=2)
print({"meta_done":True,"out":os.path.join(EXP,"meta_summary.json")})
