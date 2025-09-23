import pandas as pd, numpy as np
df=pd.read_parquet("tmp/features_tdnet_q4_smoke.parquet")
X=df.select_dtypes(include=[np.number]).drop(columns=[c for c in ["y_2x"] if c in df.columns], errors="ignore")
std=X.std(numeric_only=True)
zv = (std==0).sum()
print({"n_features":X.shape[1],"zero_var":int(zv),"nonzero_var":int((std>0).sum())})
