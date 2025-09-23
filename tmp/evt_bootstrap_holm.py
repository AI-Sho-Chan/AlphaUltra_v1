import os, json, numpy as np, pandas as pd
from scipy import stats
EXP=os.environ["EXP_DIR"]; OOF=r"reports/checks/tdnet_model_y_2x_oof.parquet"; PRC=r"data/proc/prices/jp_prices_std_compat_q4p.parquet"
thr=0.205; Hs=[5,20,60]; Ns=[5,10,20]; B=1000
o=pd.read_parquet(OOF)[["ticker","eff_date","p_raw"]]
p=pd.read_parquet(PRC, columns=["ticker","eff_date","adj_close"]).sort_values(["ticker","eff_date"])
p["next_ret"]=p.groupby("ticker")["adj_close"].pct_change().shift(-1)

def h_ret(df,H):
    g=df.groupby("ticker",group_keys=False)
    r=g["next_ret"].apply(lambda s:s.rolling(H,min_periods=H).sum()).shift(-(H-1))
    return df.assign(**{f"ret_H{H}":r})

def combo_stats(H,N):
    ph=h_ret(p.copy(),H).dropna(subset=[f"ret_H{H}"])
    sig=o.merge(ph[["ticker","eff_date",f"ret_H{H}"]],on=["ticker","eff_date"],how="inner")
    sig["pick"]=(sig["p_raw"]>=thr).astype(int)
    sig=sig.sort_values(["eff_date","p_raw"],ascending=[True,False])
    sig["rank"]=sig.groupby("eff_date")["p_raw"].rank(method="first",ascending=False)
    pick=sig[(sig["pick"]==1)&(sig["rank"]<=N)]
    if pick.empty: return {"n":0,"ann":0,"p":1.0,"ci":[0,0]}
    day=pick.groupby("eff_date")[f"ret_H{H}"].mean().values
    ann=day.mean()*(252/H)
    # ブートストラップCI（平均のpercentile法）
    if len(day)<5: ci=[ann,ann]
    else:
        bs = np.array([np.mean(np.random.choice(day, size=len(day), replace=True)) for _ in range(B)])*(252/H)
        ci=[float(np.percentile(bs,2.5)), float(np.percentile(bs,97.5))]
    pval=stats.ttest_1samp(day,0.0,alternative="greater").pvalue if len(day)>1 else 1.0
    return {"n":int(len(day)),"ann":float(ann),"p":float(pval),"ci":ci}

raw={}
for H in Hs:
    for N in Ns:
        raw[f"H{H}_N{N}"]=combo_stats(H,N)

# Holm-Bonferroni補正
m=len(raw); ordered=sorted(raw.items(), key=lambda kv: kv[1]["p"])
adj={}
for i,(k,v) in enumerate(ordered, start=1):
    adj_p=min(1.0, v["p"]*(m - i + 1))
    adj[k]={**v,"p_holm":float(adj_p)}

with open(os.path.join(EXP,"evt_ci_holm.json"),"w",encoding="utf-8") as f: json.dump(adj,f,ensure_ascii=False,indent=2)
print({"evt_ci_holm":os.path.join(EXP,"evt_ci_holm.json")})
