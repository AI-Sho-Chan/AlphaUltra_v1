import os, json, numpy as np, pandas as pd
EXP=os.environ["EXP_DIR"]; OOF=r"reports/checks/meta_y_2x_oof.parquet"; PRC=r"data/proc/prices/jp_prices_std_compat_q4p.parquet"
thr=0.355; H=20
m=pd.read_parquet(OOF)[["ticker","eff_date","p_raw"]]
p=pd.read_parquet(PRC, columns=["ticker","eff_date","adj_close"]).sort_values(["ticker","eff_date"])
p["next_ret"]=p.groupby("ticker")["adj_close"].pct_change().shift(-1)
g=p.groupby("ticker",group_keys=False)
ret=g["next_ret"].apply(lambda s:s.rolling(H,min_periods=H).sum()).shift(-(H-1))
ph=p.assign(ret=ret).dropna(subset=["ret"])

# 閾値ルール
sigA=m.merge(ph[["ticker","eff_date","ret"]],on=["ticker","eff_date"],how="inner")
sigA=sigA[sigA["p_raw"]>=thr].groupby("eff_date")["ret"].mean().resample("ME").mean()

# TOP-K
rank=m.merge(ph[["ticker","eff_date","ret"]],on=["ticker","eff_date"],how="inner").sort_values(["eff_date","p_raw"],ascending=[True,False])
rank["r"]=rank.groupby("eff_date")["p_raw"].rank(method="first",ascending=False)
out={}
for K in (5,10):
    day=rank[rank["r"]<=K].groupby("eff_date")["ret"].mean().resample("ME").mean()
    out[f"TOP{K}"]={"months":int(len(day)),"ann": float(day.mean()*12 if len(day)>0 else 0.0)}
meta={"thr":thr,"H":H,"A_thr":{"months":int(len(sigA)),"ann":float(sigA.mean()*12 if len(sigA)>0 else 0.0)}}
meta.update(out)
open(os.path.join(EXP,"meta_monthly_sizes_v2.json"),"w",encoding="utf-8").write(json.dumps(meta,ensure_ascii=False,indent=2))
print(meta)
