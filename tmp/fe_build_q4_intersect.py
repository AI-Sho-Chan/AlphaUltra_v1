import pandas as pd, pathlib

# 入力
fe_path = pathlib.Path("data/proc/features_tdnet/tdnet_event_features.parquet")
px_path = pathlib.Path("data/proc/prices/jp_prices_std_compat_slim_q4.parquet")

# 期間
win_lo, win_hi = pd.Timestamp("2013-11-01"), pd.Timestamp("2014-12-31")

# 読込
fe = pd.read_parquet(fe_path)
px = pd.read_parquet(px_path, columns=["ticker","eff_date"]).dropna()

# 正規化
fe["eff_date"] = pd.to_datetime(fe["eff_date"]).dt.normalize()
px["eff_date"] = pd.to_datetime(px["eff_date"]).dt.normalize()
fe["ticker"]   = fe["ticker"].astype(str)
px["ticker"]   = px["ticker"].astype(str)

# 期間フィルタ
fe = fe[fe["eff_date"].between(win_lo, win_hi)]

# 交差キーのみ残す（セミジョイン）
keys = px.drop_duplicates()
fe   = fe.merge(keys, on=["ticker","eff_date"], how="inner")

# サイズを確認
print({"fe_rows": len(fe), "fe_cols": len(fe.columns)})

# 出力
out = pathlib.Path("tmp/features_tdnet_q4_intersect.parquet")
out.parent.mkdir(parents=True, exist_ok=True)
fe.to_parquet(out, index=False)
print({"out": str(out)})
