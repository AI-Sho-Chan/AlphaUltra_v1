import pandas as pd, numpy as np

FE_IN = "tmp/features_tdnet_q4_smoke.parquet"   # 直前の200キー
PX    = "data/proc/prices/jp_prices_std_compat_q4p.parquet"

fe = pd.read_parquet(FE_IN)
px = pd.read_parquet(PX, columns=["ticker","eff_date","adj_close","volume"])

fe["ticker"]=fe["ticker"].astype(str)
fe["eff_date"]=pd.to_datetime(fe["eff_date"]).dt.normalize()
px["ticker"]=px["ticker"].astype(str)
px["eff_date"]=pd.to_datetime(px["eff_date"]).dt.normalize()

px = px.sort_values(["ticker","eff_date"])
g  = px.groupby("ticker", group_keys=False)

# 20バー必要な指標のみを作る（min_periods=20）。十分な履歴がない行はNaNのままにする
px["ret_5"]  = g["adj_close"].pct_change(5)
px["ret_20"] = g["adj_close"].pct_change(20)
px["ma20"]   = g["adj_close"].transform(lambda s: s.rolling(20, min_periods=20).mean())
px["std20"]  = g["adj_close"].transform(lambda s: s.rolling(20, min_periods=20).std())
px["z20"]    = (px["adj_close"] - px["ma20"]) / px["std20"]
px["mom20"]  = px["adj_close"] / g["adj_close"].shift(20) - 1.0
px["v_ma20"] = g["volume"].transform(lambda s: s.rolling(20, min_periods=20).mean())
px["v_std20"]= g["volume"].transform(lambda s: s.rolling(20, min_periods=20).std())
px["v_z20"]  = (px["volume"] - px["v_ma20"]) / px["v_std20"]

need = ["ret_5","ret_20","z20","mom20","v_z20"]
pxu  = px[["ticker","eff_date"]+need].dropna()                 # ←十分な過去が無い行は落とす
pxu  = pxu.drop_duplicates(["ticker","eff_date"])

m = fe.merge(pxu, on=["ticker","eff_date"], how="inner", validate="m:1")  # 欠損混入を避ける
for c in need: m[c] = pd.to_numeric(m[c], errors="coerce").astype("float32")

m.to_parquet("tmp/features_tdnet_q4_smoke.parquet", index=False)
print({"rows":len(m), "kept_ratio": round(len(m)/len(fe),3),
       "zero_var": int((m[need].std()==0).sum())})
