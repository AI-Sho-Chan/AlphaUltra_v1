import pandas as pd
# 学習直前の小結合を再現（スモーク200キーで十分）
fe = pd.read_parquet("tmp/features_tdnet_q4_smoke.parquet")
px = pd.read_parquet("data/proc/prices/jp_prices_std_compat_q4p.parquet",
                     columns=["ticker","eff_date","adj_close","volume","addv_3m"])
fe["eff_date"]=pd.to_datetime(fe["eff_date"]).dt.normalize()
px["eff_date"]=pd.to_datetime(px["eff_date"]).dt.normalize()
m = fe.merge(px.drop_duplicates(["ticker","eff_date"]),
             on=["ticker","eff_date"], how="left", validate="m:1")
# ラベル列の存在と非NaN数
label = "y_2x"
print({"rows":len(m), "label_present": (label in m.columns), "label_notna": int(m[label].notna().sum()) if label in m.columns else 0})
