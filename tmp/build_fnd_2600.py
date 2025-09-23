import pandas as pd, numpy as np, pathlib

# 入力：2600特徴（イベントのキー集合）
FE_EVT = "tmp/features_tdnet_q4_work.parquet"
# 価格ウィンドウ（Q4＋将来バッファ）
PX     = "data/proc/prices/jp_prices_std_compat_q4p.parquet"
# あるならJ-Quantsパーケット（例）：data/proc/fund/jq_agg_asof.parquet
JQ_OPT = "data/proc/fund/jq_agg_asof.parquet"

fe = pd.read_parquet(FE_EVT, columns=["ticker","eff_date","y_2x"])
fe["ticker"]=fe["ticker"].astype(str); fe["eff_date"]=pd.to_datetime(fe["eff_date"]).dt.normalize()

px = pd.read_parquet(PX, columns=["ticker","eff_date","adj_close","volume"])
px["ticker"]=px["ticker"].astype(str); px["eff_date"]=pd.to_datetime(px["eff_date"]).dt.normalize()
px = px.sort_values(["ticker","eff_date"])
g  = px.groupby("ticker", group_keys=False)

# 過去のみの価格派生（財務が無くても動く）
px["mom63"] = px["adj_close"]/g["adj_close"].shift(63) - 1.0
px["vol20"] = g["adj_close"].transform(lambda s: s.pct_change().rolling(20,min_periods=20).std())
px["v_lq"]  = g["volume"].transform(lambda s: s.rolling(20,min_periods=20).mean())
pxu = px[["ticker","eff_date","mom63","vol20","v_lq"]].dropna().drop_duplicates(["ticker","eff_date"])

# 任意：J-Quantsがあればas-ofでm:1マージ
try:
    jq = pd.read_parquet(JQ_OPT)
    jq["ticker"]=jq["ticker"].astype(str); jq["asof"]=pd.to_datetime(jq["asof"]).dt.normalize()
    # 代表的な財務要約（存在する列だけ拾う）
    take = [c for c in ["eps_yoy","rev_yoy","op_yoy","pbr","div_y","fcf_mgn"] if c in jq.columns]
    if take:
        jq = jq[["ticker","asof"]+take].dropna()
        # 直前営業日へスナップ
        # fe eff_date → jq asof（同一ticker）
        jq = jq.sort_values(["ticker","asof"])
        maps=[]
        for t,grp in fe.groupby("ticker", sort=False):
            d = jq.loc[jq["ticker"]==t,"asof"].to_numpy()
            if d.size==0: continue
            e = fe.loc[fe["ticker"]==t,"eff_date"].to_numpy()
            idx = np.searchsorted(d, e, side="right")-1
            ok = idx>=0
            if not ok.any(): continue
            sub = pd.DataFrame({"ticker":t,"eff_date":e[ok],"asof":d[idx[ok]]})
            maps.append(sub)
        if maps:
            snap = pd.concat(maps,ignore_index=True)
            jq = snap.merge(jq,on=["ticker","asof"],how="left",validate="m:1")
        else:
            take=[]
    else:
        take=[]
except Exception:
    take=[]

# m:1で結合
base = fe.merge(pxu, on=["ticker","eff_date"], how="inner", validate="m:1")
if take:
    base = base.merge(jq[["ticker","eff_date"]+take], on=["ticker","eff_date"], how="left", validate="m:1")

# 数値化・欠損処理
num = base.select_dtypes(include=[np.number]).columns.tolist()
base[num] = base[num].astype("float32")
base = base.dropna(subset=["mom63","vol20","v_lq"]).reset_index(drop=True)

out = pathlib.Path("tmp/features_fnd_2600.parquet")
out.parent.mkdir(parents=True, exist_ok=True)
base.to_parquet(out, index=False)
print({"rows":len(base),"feat": [c for c in base.columns if c not in ['ticker','eff_date','y_2x']]})
