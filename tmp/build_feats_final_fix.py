import pandas as pd, numpy as np, pathlib

FE="tmp/features_tdnet_q4_smoke.parquet"
PX="data/proc/prices/jp_prices_std_compat_q4p.parquet"
NEED=["ret_5","ret_20","z20","mom20","v_z20"]

fe=pd.read_parquet(FE)
px=pd.read_parquet(PX, columns=["ticker","eff_date","adj_close","volume"])
fe["ticker"]=fe["ticker"].astype(str); fe["eff_date"]=pd.to_datetime(fe["eff_date"]).dt.normalize()
px["ticker"]=px["ticker"].astype(str); px["eff_date"]=pd.to_datetime(px["eff_date"]).dt.normalize()

# 1) 直前営業日スナップ（searchsorted）
maps=[]
for t,grp in fe.groupby("ticker", sort=False):
    d_px = px.loc[px["ticker"]==t, "eff_date"].drop_duplicates().sort_values().to_numpy()
    if d_px.size==0: continue
    d_fe = grp["eff_date"].to_numpy()
    idx  = np.searchsorted(d_px, d_fe, side="right") - 1
    ok   = idx>=0
    if not ok.any(): continue
    maps.append(pd.DataFrame({"ticker":t,"eff_date":d_fe[ok],"eff_date_px":d_px[idx[ok]]}))
if not maps: raise SystemExit({"error":"no snap targets"})
fe2=pd.concat(maps,ignore_index=True).merge(fe, on=["ticker","eff_date"], how="inner", validate="m:1")

# 2) 過去特徴を段階フォールバックで構築
def build(minp):
    p=px.sort_values(["ticker","eff_date"]).copy()
    g=p.groupby("ticker",group_keys=False)
    p["ret_5"]  = g["adj_close"].pct_change(5)
    p["ret_20"] = g["adj_close"].pct_change(20)
    p["ma20"]   = g["adj_close"].transform(lambda s:s.rolling(20,min_periods=minp).mean())
    p["std20"]  = g["adj_close"].transform(lambda s:s.rolling(20,min_periods=minp).std())
    p["z20"]    = (p["adj_close"]-p["ma20"])/p["std20"]
    p["mom20"]  = p["adj_close"]/g["adj_close"].shift(20) - 1.0
    p["v_ma20"] = g["volume"].transform(lambda s:s.rolling(20,min_periods=minp).mean())
    p["v_std20"]= g["volume"].transform(lambda s:s.rolling(20,min_periods=minp).std())
    p["v_z20"]  = (p["volume"]-p["v_ma20"])/p["v_std20"]
    pxu=p[["ticker","eff_date"]+NEED].drop_duplicates(["ticker","eff_date"])
    # サフィックス固定で衝突回避
    m = fe2.merge(pxu, left_on=["ticker","eff_date_px"], right_on=["ticker","eff_date"],
                  how="left", suffixes=("", "_px"))
    # eff_date整理
    if "eff_date" in m.columns: m=m.rename(columns={"eff_date":"eff_date_right"})
    m=m.rename(columns={"eff_date_px":"eff_date"}).drop(columns=[c for c in ["eff_date_right"] if c in m.columns])
    # NEED列が無ければ欠落扱い
    missing=[c for c in NEED if c not in m.columns]
    if missing: return pd.DataFrame(), missing
    # 行フィルタ：NEEDがすべて非NaN
    m=m.dropna(subset=NEED)
    return m, []

for mp in (20,10,5):
    m, miss = build(mp)
    if len(m)>0 and not miss: break
if len(m)==0 or miss:
    raise SystemExit({"error":"feature columns missing after merge", "missing":miss, "rows":len(m)})

for c in NEED: m[c]=pd.to_numeric(m[c],errors="coerce").astype("float32")
pathlib.Path("tmp/features_tdnet_q4_smoke.parquet").write_bytes(m.to_parquet(index=False))
print({"rows":len(m),"zero_var":int((m[NEED].std(numeric_only=True)==0).sum())})
