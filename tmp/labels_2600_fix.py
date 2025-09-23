import pandas as pd

FE="tmp/features_tdnet_q4_work.parquet"     # 2600
PX="data/proc/prices/jp_prices_std_compat_q4p.parquet"

fe=pd.read_parquet(FE)
fe["ticker"]=fe["ticker"].astype(str)
fe["eff_date"]=pd.to_datetime(fe["eff_date"]).dt.normalize()

px=pd.read_parquet(PX, columns=["ticker","date","eff_date","adj_close"])
px["ticker"]=px["ticker"].astype(str)
px["date"]=pd.to_datetime(px.get("date", px["eff_date"])).dt.normalize()

# 当日の価格
base=fe.merge(px[["ticker","date","adj_close"]]
              .rename(columns={"date":"eff_date","adj_close":"px0"}),
              on=["ticker","eff_date"], how="left", validate="m:1")

# 120営業日先までの前方最大値（逆順transform再逆順）
px_sorted=px.sort_values(["ticker","date"])
fwd = px_sorted.iloc[::-1].groupby("ticker")["adj_close"] \
        .transform(lambda s: s.rolling(120, min_periods=1).max()) \
        .iloc[::-1].rename("fwd_max120")
px_sorted=px_sorted.assign(fwd_max120=fwd)

lab = base.merge(px_sorted[["ticker","date","fwd_max120"]]
                 .rename(columns={"date":"eff_date"}),
                 on=["ticker","eff_date"], how="left")

fe["y_2x"]=(lab["fwd_max120"]>=1.5*lab["px0"]).astype("Int8")
fe.to_parquet(FE, index=False)
print({"rows":len(fe), "pos": int((fe["y_2x"]==1).sum())})
