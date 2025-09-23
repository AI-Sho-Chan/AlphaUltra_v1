import pandas as pd, numpy as np

fe = pd.read_parquet("tmp/features_tdnet_q4_smoke.parquet")
px = pd.read_parquet("data/proc/prices/jp_prices_std_compat_q4p.parquet",
                     columns=["ticker","eff_date","adj_close","volume","addv_3m"])

fe["ticker"]=fe["ticker"].astype(str)
fe["eff_date"]=pd.to_datetime(fe["eff_date"]).dt.normalize()
px["ticker"]=px["ticker"].astype(str)
px["eff_date"]=pd.to_datetime(px["eff_date"]).dt.normalize()

print({"stage":"start","rows":len(fe),"pos":int((fe.get("y_2x",pd.Series([np.nan]*len(fe)))==1).sum())})

# 価格結合（m:1）
pxu = px.drop_duplicates(["ticker","eff_date"])
m = fe.merge(pxu, on=["ticker","eff_date"], how="left", validate="m:1")
print({"stage":"after_merge","rows":len(m),
       "na_adj_close":int(m["adj_close"].isna().sum()),
       "na_volume":int(m["volume"].isna().sum()),
       "na_addv3m":int(m["addv_3m"].isna().sum())})

# addv_3m 無ければ簡易作成（60営業日移動平均×移動平均出来高）
if m["addv_3m"].isna().all():
    tmp = px.sort_values(["ticker","eff_date"]).copy()
    tmp["ma_p"] = tmp.groupby("ticker")["adj_close"].transform(lambda s: s.rolling(60,min_periods=1).mean())
    tmp["ma_v"] = tmp.groupby("ticker")["volume"].transform(lambda s: s.rolling(60,min_periods=1).mean())
    tmp["addv_3m"] = (tmp["ma_p"]*tmp["ma_v"]).astype("float32")
    m = m.drop(columns=["addv_3m"]).merge(tmp[["ticker","eff_date","addv_3m"]],
                                          on=["ticker","eff_date"], how="left", validate="m:1")

# 最小フィルタ（NaN除去のみ）
keep = m.dropna(subset=["adj_close","volume","addv_3m","y_2x"])
print({"stage":"dropna","rows":len(keep),"pos":int((keep["y_2x"]==1).sum())})

# 参考：流動性が理由かを確認
loose = keep[keep["addv_3m"]>0]
print({"stage":"liquidity_loose(addv_3m>0)","rows":len(loose),"pos":int((loose["y_2x"]==1).sum())})
