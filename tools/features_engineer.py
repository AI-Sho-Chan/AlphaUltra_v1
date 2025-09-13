import pandas as pd, numpy as np, pathlib

ROOT = pathlib.Path("C:/AI/AlphaUltra")
fpath = ROOT/"data/gold/features_sample.parquet"
lpath = ROOT/"data/gold/labels_sample.parquet"
of_path = ROOT/"data/gold/features_eng.parquet"
ol_path = ROOT/"data/gold/labels_eng.parquet"

f = pd.read_parquet(fpath); y = pd.read_parquet(lpath)

def z(x):
    s = x.std(ddof=1)
    return (x - x.mean())/s if s and s != 0 else 0

f["zscore_scs"] = f.groupby("ticker")["scs"].transform(z)
f["zscore_sent"] = f.groupby("ticker")["sent"].transform(z)
f["vol_bucket"] = pd.qcut(np.log1p(f["vol"]), q=5, labels=False, duplicates="drop")

f.to_parquet(of_path, index=False)
y.to_parquet(ol_path, index=False)
print("features_eng/labels_eng written")

