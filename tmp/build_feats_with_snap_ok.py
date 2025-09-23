import pandas as pd, numpy as np, pathlib

FE="tmp/features_tdnet_q4_smoke.parquet"
PX="data/proc/prices/jp_prices_std_compat_q4p.parquet"

fe=pd.read_parquet(FE)
px=pd.read_parquet(PX, columns=["ticker","eff_date","adj_close","volume"])

fe["ticker"]=fe["ticker"].astype(str)
fe["eff_date"]=pd.to_datetime(fe["eff_date"]).dt.normalize()
px["ticker"]=px["ticker"].astype(str)
px["eff_date"]=pd.to_datetime(px["eff_date"]).dt.normalize()

# --- 1) 直前営業日へスナップ（per ticker, searchsorted） ---
maps=[]
for tkr,grp in fe.groupby("ticker", sort=False):
    d_px = px.loc[px["ticker"]==tkr, "eff_date"].drop_duplicates().sort_values().to_numpy()
    if d_px.size==0: continue
    d_fe = grp["eff_date"].to_numpy()
    idx  = np.searchsorted(d_px, d_fe, side="right") - 1
    ok   = idx>=0
    if not ok.any(): continue
    snap = pd.DataFrame({
        "ticker": tkr,
        "eff_date": d_fe[ok],
        "eff_date_px": d_px[idx[ok]]
    })
    maps.append(snap)
if not maps:
    raise SystemExit({"error":"no snap targets"})
snap = pd.concat(maps, ignore_index=True)
fe2  = fe.merge(snap, on=["ticker","eff_date"], how="inner", validate="m:1")

# --- 2) 価格から“過去のみ”の特徴を作成（min_periods 20→10 フォールバック） ---
def build(minp):
    p = px.sort_values(["ticker","eff_date"]).copy()
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
    pxu = p[["ticker","eff_date"]+need].dropna(subset=need).drop_duplicates(["ticker","eff_date"])
    m   = fe2.merge(pxu, left_on=["ticker","eff_date_px"], right_on=["ticker","eff_date"],
                    how="inner", validate="m:1").drop(columns=["eff_date"]).rename(columns={"eff_date_px":"eff_date"})
    return m, need

m, need = build(20)
if len(m)==0:
    m, need = build(10)

for c in need:
    m[c] = pd.to_numeric(m[c], errors="coerce").astype("float32")

out = pathlib.Path("tmp/features_tdnet_q4_smoke.parquet")
m.to_parquet(out, index=False)
print({"rows":len(m), "zero_var": int((m[need].std(numeric_only=True)==0).sum())})
