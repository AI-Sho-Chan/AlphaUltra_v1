import pandas as pd, numpy as np, pathlib

FE="tmp/features_tdnet_q4_smoke.parquet"
PX="data/proc/prices/jp_prices_std_compat_q4p.parquet"
NEED=["ret_5","ret_20","z20","mom20","v_z20"]

fe=pd.read_parquet(FE)
px=pd.read_parquet(PX, columns=["ticker","eff_date","adj_close","volume"])
fe["ticker"]=fe["ticker"].astype(str); fe["eff_date"]=pd.to_datetime(fe["eff_date"]).dt.normalize()
px["ticker"]=px["ticker"].astype(str); px["eff_date"]=pd.to_datetime(px["eff_date"]).dt.normalize()

# 直前営業日へスナップ（searchsorted）
maps=[]
for t,grp in fe.groupby("ticker", sort=False):
    d_px = px.loc[px["ticker"]==t,"eff_date"].drop_duplicates().sort_values().to_numpy()
    if d_px.size==0: continue
    d_fe = grp["eff_date"].to_numpy()
    idx  = np.searchsorted(d_px, d_fe, side="right") - 1
    ok   = idx>=0
    if not ok.any(): continue
    maps.append(pd.DataFrame({"ticker":t,"eff_date":d_fe[ok],"eff_date_px":d_px[idx[ok]]}))
if not maps: raise SystemExit({"error":"no snap targets"})
snap=pd.concat(maps,ignore_index=True)

# fe側の同名特徴は一旦除去（列衝突回避）
drop_cols=[c for c in NEED+["ret_1"] if c in fe.columns]
fe_clean=fe.drop(columns=drop_cols)

# 過去特徴（段階フォールバック：20→10→5）
def build(minp:int):
    p=px.sort_values(["ticker","eff_date"]).copy()
    g=p.groupby("ticker",group_keys=False)
    p["ret_5"]  = g["adj_close"].pct_change(5)
    p["ret_20"] = g["adj_close"].pct_change(20)
    p["ma20"]   = g["adj_close"].transform(lambda s:s.rolling(20,min_periods=minp).mean())
    p["std20"]  = g["adj_close"].transform(lambda s:s.rolling(20,min_periods=minp).std())
    p["z20"]    = (p["adj_close"]-p["ma20"])/p["std20"]
    p["mom20"]  = p["adj_close"]/g["adj_close"].shift(20)-1.0
    p["v_ma20"] = g["volume"].transform(lambda s:s.rolling(20,min_periods=minp).mean())
    p["v_std20"]= g["volume"].transform(lambda s:s.rolling(20,min_periods=minp).std())
    p["v_z20"]  = (p["volume"]-p["v_ma20"])/p["v_std20"]
    # 必要列だけ、衝突回避で fx_ プレフィックス
    pxu = p[["ticker","eff_date"]+NEED].dropna(subset=NEED).drop_duplicates(["ticker","eff_date"])
    pxu = pxu.rename(columns={c:f"fx_{c}" for c in NEED})
    # スナップ結果と m:1 で結合 → eff_date をスナップ日に統一
    m = snap.merge(pxu, left_on=["ticker","eff_date_px"], right_on=["ticker","eff_date"], how="inner", validate="m:1")
    m = m.drop(columns=["eff_date"]).rename(columns={"eff_date_px":"eff_date"})
    # 元の fe 情報を戻す（キーは ticker,eff_date）
    m = m.merge(fe_clean.drop(columns=["eff_date"]), on="ticker", how="left") \
         .drop_duplicates(subset=["ticker","eff_date"])
    # fx_ を元名へ
    have = [f"fx_{c}" for c in NEED if f"fx_{c}" in m.columns]
    if not have: return pd.DataFrame()
    m = m.rename(columns={f"fx_{c}":c for c in NEED if f"fx_{c}" in m.columns})
    # 最終型・欠損除去
    for c in NEED: 
        if c in m.columns: m[c]=pd.to_numeric(m[c],errors="coerce")
    m = m.dropna(subset=[c for c in NEED if c in m.columns])
    return m

m=pd.DataFrame()
for mp in (20,10,5):
    m=build(mp)
    if len(m)>0: break
if len(m)==0:
    raise SystemExit({"error":"no rows after feature build"})

# キャスト・保存
for c in NEED:
    if c in m.columns: m[c]=m[c].astype("float32")
out=pathlib.Path("tmp/features_tdnet_q4_smoke.parquet")
m.to_parquet(out, index=False)
print({"rows":len(m),"zero_var": int((m[[c for c in NEED if c in m.columns]].std(numeric_only=True)==0).sum())})
