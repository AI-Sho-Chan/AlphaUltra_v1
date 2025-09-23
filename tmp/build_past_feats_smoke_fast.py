import pandas as pd, numpy as np, pathlib

FE_IN = "tmp/features_tdnet_q4_smoke.parquet"
PX    = "data/proc/prices/jp_prices_std_compat_q4p.parquet"

fe = pd.read_parquet(FE_IN)
fe["ticker"]   = fe["ticker"].astype(str)
fe["eff_date"] = pd.to_datetime(fe["eff_date"]).dt.normalize()

# 必要分だけ価格を読む（対象ティッカー過去120営業日バッファ）
tickers = fe["ticker"].unique().tolist()
dmin, dmax = fe["eff_date"].min(), fe["eff_date"].max()
read_lo = dmin - pd.tseries.offsets.BDay(180)   # 余裕を持たせる
px = pd.read_parquet(PX, columns=["ticker","eff_date","adj_close","volume"])
px["ticker"]   = px["ticker"].astype(str)
px["eff_date"] = pd.to_datetime(px["eff_date"]).dt.normalize()
px = px[(px["ticker"].isin(tickers)) & (px["eff_date"].between(read_lo, dmax))].copy()

# ソート過去のみでローリング（min_periods=20）。不足行は後で落とす
px.sort_values(["ticker","eff_date"], inplace=True)
g = px.groupby("ticker", group_keys=False)
px["ret_5"]   = g["adj_close"].pct_change(5)
px["ret_20"]  = g["adj_close"].pct_change(20)
px["ma20"]    = g["adj_close"].transform(lambda s: s.rolling(20, min_periods=20).mean())
px["std20"]   = g["adj_close"].transform(lambda s: s.rolling(20, min_periods=20).std())
px["z20"]     = (px["adj_close"] - px["ma20"]) / px["std20"]
px["mom20"]   = px["adj_close"] / g["adj_close"].shift(20) - 1.0
px["v_ma20"]  = g["volume"].transform(lambda s: s.rolling(20, min_periods=20).mean())
px["v_std20"] = g["volume"].transform(lambda s: s.rolling(20, min_periods=20).std())
px["v_z20"]   = (px["volume"] - px["v_ma20"]) / px["v_std20"]

need = ["ret_5","ret_20","z20","mom20","v_z20"]
pxu  = px[["ticker","eff_date"]+need].drop_duplicates(["ticker","eff_date"])

# m:1 セミジョインで結合（不足は落とす）
m = fe.merge(pxu, on=["ticker","eff_date"], how="inner", validate="m:1").copy()
m.dropna(subset=need, inplace=True)
for c in need: m[c] = pd.to_numeric(m[c], errors="coerce").astype("float32")

out = pathlib.Path("tmp/features_tdnet_q4_smoke.parquet")
m.to_parquet(out, index=False)
print({"rows":len(m), "kept_ratio": round(len(m)/len(fe),3),
       "zero_var": int((m[need].std(numeric_only=True)==0).sum()),
       "n_features": len(need)})
