import pandas as pd, numpy as np, pathlib

# 入力
fe = pd.read_parquet("tmp/features_tdnet_q4_smoke.parquet")
px = pd.read_parquet("data/proc/prices/jp_prices_std_compat_q4p.parquet",
                     columns=["ticker","date","eff_date","adj_close"])

# 正規化
fe["ticker"]=fe["ticker"].astype(str)
fe["eff_date"]=pd.to_datetime(fe["eff_date"]).dt.normalize()
px["ticker"]=px["ticker"].astype(str)
px["date"]=pd.to_datetime(px.get("date", px["eff_date"])).dt.normalize()

# 先にその日の価格を取得
today_px = px[["ticker","date","adj_close"]].rename(columns={"date":"eff_date","adj_close":"px0"})
keys = fe[["ticker","eff_date"]].drop_duplicates()
base = keys.merge(today_px, on=["ticker","eff_date"], how="left")

# 60営業日先までの前方最大値を算出
px = px.sort_values(["ticker","date"])
g = px.groupby("ticker", group_keys=False)
# 後ろからrolling max→元順へ戻す
px_rev = px.iloc[::-1].copy()
px_rev["fwd_max60"] = g["adj_close"].apply(lambda s: s.rolling(60, min_periods=1).max())
px["fwd_max60"] = px_rev["fwd_max60"].iloc[::-1].values

fwd = px[["ticker","date","fwd_max60"]].rename(columns={"date":"eff_date"})
lab = base.merge(fwd, on=["ticker","eff_date"], how="left")
lab["y_2x"] = (lab["fwd_max60"] >= 2.0*lab["px0"]).astype("Int8")

# スモーク特徴へ結合して上書き
fe2 = fe.merge(lab[["ticker","eff_date","y_2x"]], on=["ticker","eff_date"], how="left")
fe2.to_parquet("tmp/features_tdnet_q4_smoke.parquet", index=False)

print({"rows":len(fe2), "label_pos": int((fe2["y_2x"]==1).sum()), "label_notna": int(fe2["y_2x"].notna().sum())})
