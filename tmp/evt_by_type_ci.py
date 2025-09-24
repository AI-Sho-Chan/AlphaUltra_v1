import os, json, numpy as np, pandas as pd
from scipy import stats

EXP=os.environ["EXP_DIR"]
OOF=r"reports/checks/tdnet_model_y_2x_oof.parquet"      # p_raw
FEV=r"tmp/features_tdnet_q4_work.parquet"               # event_type/event_cat/…
PRC=r"data/proc/prices/jp_prices_std_compat_q4p.parquet"
thr=0.205
Hs=[20,60]
B=1000

o=pd.read_parquet(OOF)[["ticker","eff_date","p_raw"]]
f=pd.read_parquet(FEV, columns=["ticker","eff_date","event_type","event_cat"]).dropna(subset=["event_type"])
p=pd.read_parquet(PRC, columns=["ticker","eff_date","adj_close"]).sort_values(["ticker","eff_date"])
p["next_ret"]=p.groupby("ticker")["adj_close"].pct_change().shift(-1)

def h_ret(df,H):
    g=df.groupby("ticker",group_keys=False)
    r=g["next_ret"].apply(lambda s:s.rolling(H,min_periods=H).sum()).shift(-(H-1))
    return df.assign(ret=r)

res={}
for H in Hs:
    ph=h_ret(p.copy(),H).dropna(subset=["ret"])
    sig=o.merge(f, on=["ticker","eff_date"], how="inner").merge(
        ph[["ticker","eff_date","ret"]], on=["ticker","eff_date"], how="inner")
    sig=sig[sig["p_raw"]>=thr]
    for key in ["event_type","event_cat"]:
        out={}
        for grp,val in sig.groupby(key):
            day=val.groupby("eff_date")["ret"].mean().values
            if len(day)<5: 
                out[str(grp)]={"n":int(len(day)),"ann":0,"ci":[0,0],"p":1.0}; continue
            ann=day.mean()*(252/H)
            bs=np.array([np.mean(np.random.choice(day,len(day),True)) for _ in range(B)])*(252/H)
            lo,hi=np.percentile(bs,[2.5,97.5])
            pval=stats.ttest_1samp(day,0.0,alternative="greater").pvalue
            out[str(grp)]={"n":int(len(day)),"ann":float(ann),"ci":[float(lo),float(hi)],"p":float(pval)}
        # Holm補正
        items=sorted(out.items(), key=lambda kv: kv[1]["p"])
        m=len(items); adj={}
        for i,(g,rec) in enumerate(items,1):
            rec2=rec.copy(); rec2["p_holm"]=min(1.0, rec["p"]*(m-i+1)); adj[g]=rec2
        res[f"H{H}_{key}"]=adj

json.dump(res, open(os.path.join(EXP,"evt_by_type_ci.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=2)
print({"evt_by_type_ci":os.path.join(EXP,"evt_by_type_ci.json")})
