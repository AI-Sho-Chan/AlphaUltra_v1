import os, json, numpy as np, pandas as pd
from scipy import stats
EXP=os.environ["EXP_DIR"]; OOF=r"reports/checks/meta_y_2x_oof.parquet"; PRC=r"data/proc/prices/jp_prices_std_compat_q4p.parquet"
thr=0.355; H=20; K_list=[3,5,10]

m=pd.read_parquet(OOF)[["ticker","eff_date","p_raw"]]
p=pd.read_parquet(PRC, columns=["ticker","eff_date","adj_close"]).sort_values(["ticker","eff_date"])
p["next_ret"]=p.groupby("ticker")["adj_close"].pct_change().shift(-1)
g=p.groupby("ticker",group_keys=False)
ret=g["next_ret"].apply(lambda s:s.rolling(H,min_periods=H).sum()).shift(-(H-1))
ph=p.assign(ret=ret).dropna(subset=["ret"])

# ルールA: 閾値
sigA=m.merge(ph[["ticker","eff_date","ret"]],on=["ticker","eff_date"],how="inner")
sigA=sigA[sigA["p_raw"]>=thr].groupby("eff_date")["ret"].mean()
mretA=sigA.resample("ME").mean()

# ルールB: TOP-K（等金額）
outB={}
rank=m.merge(ph[["ticker","eff_date","ret"]],on=["ticker","eff_date"],how="inner") \
       .sort_values(["eff_date","p_raw"],ascending=[True,False])
rank["r"]=rank.groupby("eff_date")["p_raw"].rank(method="first",ascending=False)
for K in K_list:
    day = rank[rank["r"]<=K].groupby("eff_date")["ret"].mean()
    outB[f"TOP{K}"]=day.resample("ME").mean()

def ci_monthly(x):
    if len(x)<6: return {"n":int(len(x)),"ann":0,"ci":[0,0]}
    ann=float(x.mean()*12)
    bs=np.array([np.mean(np.random.choice(x,size=len(x),replace=True)) for _ in range(2000)])*12
    return {"n":int(len(x)),"ann":ann,"ci":[float(np.percentile(bs,2.5)),float(np.percentile(bs,97.5))]}

rep={"thr":thr,"H":H,"A_thr":ci_monthly(mretA)}
for k,ser in outB.items(): rep[k]=ci_monthly(ser)

open(os.path.join(EXP,"meta_monthly_ci_v2.json"),"w",encoding="utf-8").write(json.dumps(rep,ensure_ascii=False,indent=2))
print({"meta_monthly_ci_v2":os.path.join(EXP,"meta_monthly_ci_v2.json")})
