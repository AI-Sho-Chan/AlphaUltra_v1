import pandas as pd, numpy as np, pathlib

# 入力
FE_IN = "tmp/features_tdnet_q4_smoke.parquet"  # 200キー
PX    = "data/proc/prices/jp_prices_std_compat_q4p.parquet"

fe = pd.read_parquet(FE_IN)
px = pd.read_parquet(PX, columns=["ticker","eff_date","adj_close","volume"])

# 正規化
fe["ticker"]=fe["ticker"].astype(str)
fe["eff_date"]=pd.to_datetime(fe["eff_date"]).dt.normalize()
px["ticker"]=px["ticker"].astype(str)
px["eff_date"]=pd.to_datetime(px["eff_date"]).dt.normalize()

# ティッカーごとに過去のみで特徴を作る
px = px.sort_values(["ticker","eff_date"])
g  = px.groupby("ticker", group_keys=False)

# リターン系（過去のみ）
px["ret_1"]  = g["adj_close"].pct_change(1)
px["ret_5"]  = g["adj_close"].pct_change(5)
px["ret_20"] = g["adj_close"].pct_change(20)

# 移動平均・乖離・モメンタム（過去のみ）
px["ma20"]   = g["adj_close"].transform(lambda s: s.rolling(20,min_periods=5).mean())
px["std20"]  = g["adj_close"].transform(lambda s: s.rolling(20,min_periods=5).std())
px["z20"]    = (px["adj_close"] - px["ma20"]) / px["std20"]
px["mom20"]  = px["adj_close"] / g["adj_close"].shift(20) - 1.0

# 出来高系
px["v_ma20"]  = g["volume"].transform(lambda s: s.rolling(20,min_periods=5).mean())
px["v_std20"] = g["volume"].transform(lambda s: s.rolling(20,min_periods=5).std())
px["v_z20"]   = (px["volume"] - px["v_ma20"]) / px["v_std20"]

# 当日行をキー結合（m:1）。将来情報は含まれない。
cols = ["ticker","eff_date","ret_1","ret_5","ret_20","z20","mom20","v_z20"]
pxu  = px[cols].dropna().drop_duplicates(["ticker","eff_date"])
fe2  = fe.merge(pxu, on=["ticker","eff_date"], how="left", validate="m:1")

# 欠損は0埋め（スモーク用）
num_cols = ["ret_1","ret_5","ret_20","z20","mom20","v_z20"]
for c in num_cols: fe2[c] = pd.to_numeric(fe2[c], errors="coerce").fillna(0.0).astype("float32")

# 上書き保存
out = pathlib.Path("tmp/features_tdnet_q4_smoke.parquet")
fe2.to_parquet(out, index=False)
print({"rows":len(fe2), "n_feat":len(num_cols), "zero_var": int((fe2[num_cols].std()==0).sum())})
