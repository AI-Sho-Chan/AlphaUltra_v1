import os, json, pandas as pd, numpy as np
from scipy import stats
EXP = os.environ["EXP_DIR"]
OOF = r"reports/checks/tdnet_model_y_2x_oof.parquet"
PRC = r"data/proc/prices/jp_prices_std_compat_q4p.parquet"
thr, Hs, Ns = 0.205, [5,20,60], [5,10,20]

o = pd.read_parquet(OOF)[["ticker","eff_date","p_raw"]]
p = pd.read_parquet(PRC, columns=["ticker","eff_date","adj_close"]).sort_values(["ticker","eff_date"])
p["next_ret"] = p.groupby("ticker")["adj_close"].pct_change().shift(-1)

def h_ret(df,H):
    g=df.groupby("ticker",group_keys=False)
    r=g["next_ret"].apply(lambda s:s.rolling(H,min_periods=H).sum()).shift(-(H-1))
    return df.assign(**{f"ret_H{H}":r})

res={}
for H in Hs:
    ph=h_ret(p.copy(),H).dropna(subset=[f"ret_H{H}"])
    sig=o.merge(ph[["ticker","eff_date",f"ret_H{H}"]],on=["ticker","eff_date"],how="inner")
    sig["pick"]=(sig["p_raw"]>=thr).astype(int)
    sig=sig.sort_values(["eff_date","p_raw"],ascending=[True,False])
    sig["rank"]=sig.groupby("eff_date")["p_raw"].rank(method="first",ascending=False)
    for N in Ns:
        pick=sig[(sig["pick"]==1)&(sig["rank"]<=N)]
        if pick.empty:
            res[f"H{H}_N{N}"]={"coverage":0,"ann_excess":0,"t_p":1.0,"n_trades":0}; continue
        day=pick.groupby("eff_date")[f"ret_H{H}"].mean()
        mu, n = day.mean(), len(day)
        ann_excess = float(mu*(252/H))
        t_p = float(stats.ttest_1samp(day,0.0,alternative="greater").pvalue) if n>1 else 1.0
        res[f"H{H}_N{N}"]={"coverage":float(len(pick)/len(sig)),"ann_excess":ann_excess,"t_p":t_p,"n_trades":int(len(pick))}
with open(os.path.join(EXP,"evt_summary.json"),"w",encoding="utf-8") as f: json.dump(res,f,ensure_ascii=False,indent=2)
print({"evt_done":True,"out":os.path.join(EXP,"evt_summary.json")})
