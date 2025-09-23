SRC="tmp/features_tdnet_q4_intersect_unique.parquet"  # 2600キー
DST="tmp/features_tdnet_q4_work.parquet"
import pandas as pd; pd.read_parquet(SRC).to_parquet(DST, index=False)
print({"rows":len(pd.read_parquet(DST))})
