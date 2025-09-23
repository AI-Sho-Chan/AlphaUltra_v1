import os, json, pandas as pd, numpy as np, pathlib
ENV=r".secrets\jq.env"
def load_env(p):
    d={}
    if not os.path.exists(p): return d
    with open(p, encoding="utf-8") as f:
        for line in f:
            s=line.strip()
            if not s or s.startswith("#") or "=" not in s: continue
            k,v=s.split("=",1); d[k.strip()]=v.strip()
    return d

env = load_env(ENV)
if not env.get("refreshToken"):
    print({"jq":"missing","action":".secrets/jq.env に refreshToken を設定"})
    raise SystemExit(0)

# 以降は前回と同じダミーas-of（価格連動）。実API化は後続タスク。
FE=r"tmp/features_tdnet_q4_work.parquet"; PX=r"data/proc/prices/jp_prices_std_compat_q4p.parquet"
fe=pd.read_parquet(FE, columns=["ticker","eff_date","y_2x"]).assign(
    ticker=lambda x:x["ticker"].astype(str), eff_date=lambda x:pd.to_datetime(x["eff_date"]).dt.normalize()
)
px=pd.read_parquet(PX, columns=["ticker","eff_date","adj_close","volume"]).assign(
    ticker=lambda x:x["ticker"].astype(str), eff_date=lambda x:pd.to_datetime(x["eff_date"]).dt.normalize()
).sort_values(["ticker","eff_date"])

g=px.groupby("ticker",group_keys=False)
px["pr_ma20"]=g["adj_close"].transform(lambda s:s.rolling(20,min_periods=20).mean())
px["pr_gr20"]=px["adj_close"]/g["adj_close"].shift(20)-1.0
jq=px[["ticker","eff_date","pr_ma20","pr_gr20"]].dropna()

# 直前営業日スナップ
maps=[]
for t,grp in fe.groupby("ticker", sort=False):
    d=jq.loc[jq["ticker"]==t,"eff_date"].drop_duplicates().sort_values().to_numpy()
    if d.size==0: continue
    e=grp["eff_date"].to_numpy()
    idx=np.searchsorted(d,e,side="right")-1
    ok=idx>=0
    if not ok.any(): continue
    maps.append(pd.DataFrame({"ticker":t,"eff_date":e[ok],"asof":d[idx[ok]]}))
snap=pd.concat(maps,ignore_index=True) if maps else pd.DataFrame(columns=["ticker","eff_date","asof"])
fnd=fe.merge(snap,on=["ticker","eff_date"],how="inner",validate="m:1").merge(
     jq.rename(columns={"eff_date":"asof"}),on=["ticker","asof"],how="left",validate="m:1")

# 価格最小特徴の併用
px2=px.copy(); g2=px2.groupby("ticker",group_keys=False)
px2["mom63"]=px2["adj_close"]/g2["adj_close"].shift(63)-1.0
px2["vol20"]=g2["adj_close"].transform(lambda s:s.pct_change().rolling(20,min_periods=20).std())
px2["v_lq"]=g2["volume"].transform(lambda s:s.rolling(20,min_periods=20).mean())
pxu=px2[["ticker","eff_date","mom63","vol20","v_lq"]].dropna().drop_duplicates(["ticker","eff_date"])
fnd=fnd.merge(pxu,on=["ticker","eff_date"],how="left",validate="m:1").dropna()

out=pathlib.Path(r"tmp/features_fnd_2600.parquet"); out.parent.mkdir(parents=True,exist_ok=True)
fnd.to_parquet(out,index=False)
print({"fnd_rows":len(fnd),"cols":list(fnd.columns)[:8]})
