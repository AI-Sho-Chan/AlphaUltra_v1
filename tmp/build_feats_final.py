import pandas as pd, numpy as np, pathlib

FE="tmp/features_tdnet_q4_smoke.parquet"
PX="data/proc/prices/jp_prices_std_compat_q4p.parquet"
NEED=["ret_5","ret_20","z20","mom20","v_z20"]

fe=pd.read_parquet(FE)
px=pd.read_parquet(PX, columns=["ticker","eff_date","adj_close","volume"])

fe["ticker"]=fe["ticker"].astype(str)
fe["eff_date"]=pd.to_datetime(fe["eff_date"]).dt.normalize()
px["ticker"]=px["ticker"].astype(str)
px["eff_date"]=pd.to_datetime(px["eff_date"]).dt.normalize()

# --- snap to prior trading day per ticker ---
maps=[]
for tkr,grp in fe.groupby("ticker", sort=False):
    d_px = px.loc[px["ticker"]==tkr, "eff_date"].drop_duplicates().sort_values().to_numpy()
    if d_px.size==0: continue
    d_fe = grp["eff_date"].to_numpy()
    idx  = np.searchsorted(d_px, d_fe, side="right") - 1
    ok   = idx>=0
    if not ok.any(): continue
    maps.append(pd.DataFrame({"ticker":tkr,"eff_date":d_fe[ok],"eff_date_px":d_px[idx[ok]]}))
if not maps:
    raise SystemExit({"error":"no snap targets"})
fe2=pd.concat(maps,ignore_index=True).merge(fe, on=["ticker","eff_date"], how="inner", validate="m:1")

def build(minp:int):
    p=px.sort_values(["ticker","eff_date"]).copy()
    g=p.groupby("ticker",group_keys=False)
    p["ret_5"] = g["adj_close"].pct_change(5)
    p["ret_20"]= g["adj_close"].pct_change(20)
    p["ma20"]  = g["adj_close"].transform(lambda s:s.rolling(20,min_periods=minp).mean())
    p["std20"] = g["adj_close"].transform(lambda s:s.rolling(20,min_periods=minp).std())
    p["z20"]   = (p["adj_close"]-p["ma20"])/p["std20"]
    p["mom20"] = p["adj_close"]/g["adj_close"].shift(20)-1.0
    p["v_ma20"]= g["volume"].transform(lambda s:s.rolling(20,min_periods=minp).mean())
    p["v_std20"]=g["volume"].transform(lambda s:s.rolling(20,min_periods=minp).std())
    p["v_z20"] = (p["volume"]-p["v_ma20"])/p["v_std20"]
    pxu = p[["ticker","eff_date"]+NEED].dropna(subset=NEED).drop_duplicates(["ticker","eff_date"])
    m   = fe2.merge(pxu, left_on=["ticker","eff_date_px"], right_on=["ticker","eff_date"],
                    how="inner", validate="m:1")
    # unify eff_date
    if "eff_date" in m.columns: m=m.rename(columns={"eff_date":"eff_date_right"})
    m=m.rename(columns={"eff_date_px":"eff_date"})
    if "eff_date_right" in m.columns: m=m.drop(columns=["eff_date_right"])
    # types
    for c in NEED: m[c]=pd.to_numeric(m[c],errors="coerce")
    m=m.dropna(subset=NEED)
    return m

m=None
for mp in (20,10,5):
    m=build(mp)
    # 必要列が揃い、かつゼロ分散でない列があるなら採用
    if len(m)>0 and (m[NEED].std(numeric_only=True)>0).any():
        break

if m is None or len(m)==0:
    raise SystemExit({"error":"no rows after feature build (check price window and tickers)"} )

# 最終キャスト
for c in NEED: m[c]=m[c].astype("float32")

pathlib.Path("tmp/features_tdnet_q4_smoke.parquet").write_bytes(m.to_parquet(index=False))
print({"rows":len(m),"zero_var":int((m[NEED].std(numeric_only=True)==0).sum())})
