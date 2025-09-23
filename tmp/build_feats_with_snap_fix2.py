import pandas as pd, pathlib

FE="tmp/features_tdnet_q4_smoke.parquet"
PX="data/proc/prices/jp_prices_std_compat_q4p.parquet"

fe=pd.read_parquet(FE)
px=pd.read_parquet(PX, columns=["ticker","eff_date","adj_close","volume"])

fe["ticker"]=fe["ticker"].astype(str)
fe["eff_date"]=pd.to_datetime(fe["eff_date"]).dt.normalize()
px["ticker"]=px["ticker"].astype(str)
px["eff_date"]=pd.to_datetime(px["eff_date"]).dt.normalize()

# 1) 厳密ソート（左・右ともに by + on）
fe_s = fe.dropna(subset=["ticker","eff_date"]).sort_values(["ticker","eff_date"]).reset_index(drop=True)
px_s = px.dropna(subset=["ticker","eff_date"]).sort_values(["ticker","eff_date"]).reset_index(drop=True)

# 左キーを抽出（重複許容、順序維持）
left = fe_s[["ticker","eff_date"]].copy()
right= px_s[["ticker","eff_date"]].drop_duplicates().sort_values(["ticker","eff_date"]).reset_index(drop=True)

# 2) 直前営業日にスナップ（by も on もソート済み）
snap = pd.merge_asof(left, right, by="ticker", left_on="eff_date", right_on="eff_date",
                     direction="backward", allow_exact_matches=True)
snap = pd.concat([fe_s, snap["eff_date_y"].rename("eff_date_px")], axis=1).dropna(subset=["eff_date_px"])
snap["eff_date_px"] = pd.to_datetime(snap["eff_date_px"]).dt.normalize()

# 3) “過去のみ”で価格特徴を生成（足りなければ min_periods=10）
def build(minp):
    p = px_s.copy()
    g = p.groupby("ticker", group_keys=False)
    p["ret_5"]  = g["adj_close"].pct_change(5)
    p["ret_20"] = g["adj_close"].pct_change(20)
    p["ma20"]   = g["adj_close"].transform(lambda s:s.rolling(20,min_periods=minp).mean())
    p["std20"]  = g["adj_close"].transform(lambda s:s.rolling(20,min_periods=minp).std())
    p["z20"]    = (p["adj_close"]-p["ma20"])/p["std20"]
    p["mom20"]  = p["adj_close"]/g["adj_close"].shift(20) - 1.0
    p["v_ma20"] = g["volume"].transform(lambda s:s.rolling(20,min_periods=minp).mean())
    p["v_std20"]= g["volume"].transform(lambda s:s.rolling(20,min_periods=minp).std())
    p["v_z20"]  = (p["volume"]-p["v_ma20"])/p["v_std20"]
    need=["ret_5","ret_20","z20","mom20","v_z20"]
    pxu=p[["ticker","eff_date"]+need].dropna(subset=need).drop_duplicates(["ticker","eff_date"])
    m = snap.merge(pxu, left_on=["ticker","eff_date_px"], right_on=["ticker","eff_date"],
                   how="inner", validate="m:1").drop(columns=["eff_date"]).rename(columns={"eff_date_px":"eff_date"})
    return m, need

m, need = build(20)
if len(m)==0: m, need = build(10)

for c in need: m[c]=pd.to_numeric(m[c],errors="coerce").astype("float32")
pathlib.Path("tmp/features_tdnet_q4_smoke.parquet").write_bytes(m.to_parquet(index=False))
print({"rows":len(m),"zero_var":int((m[need].std(numeric_only=True)==0).sum())})
