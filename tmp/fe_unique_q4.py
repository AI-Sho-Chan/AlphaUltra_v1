import pandas as pd, pathlib, numpy as np

src = pathlib.Path("tmp/features_tdnet_q4_intersect.parquet")
fe  = pd.read_parquet(src)

# 正規化
fe["ticker"] = fe["ticker"].astype(str)
fe["eff_date"] = pd.to_datetime(fe["eff_date"]).dt.normalize()

# 主要数値列をfloat32に（軽量化）
for c in fe.columns:
    if c not in ("ticker","eff_date") and np.issubdtype(fe[c].dtype, np.number):
        fe[c] = pd.to_numeric(fe[c], errors="coerce").astype("float32")

# ユニーク化（同一キーは最新行を採用）
fe = fe.sort_values(["ticker","eff_date"]).drop_duplicates(["ticker","eff_date"], keep="last")

out = pathlib.Path("tmp/features_tdnet_q4_intersect_unique.parquet")
fe.to_parquet(out, index=False)

print({"rows": len(fe), "cols": len(fe.columns), "out": str(out)})
