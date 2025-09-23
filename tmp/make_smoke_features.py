import pandas as pd, pathlib
fe = pd.read_parquet("tmp/features_tdnet_q4_intersect_unique.parquet")
fe = fe.sort_values(["ticker","eff_date"]).groupby("ticker", as_index=False).head(5)  # ≒2000→さらに縮める
fe = fe.sort_values(["eff_date","ticker"]).head(200)  # 固定200キー
out = pathlib.Path("tmp/features_tdnet_q4_smoke.parquet")
fe.to_parquet(out, index=False)
print({"rows": len(fe), "out": str(out)})
