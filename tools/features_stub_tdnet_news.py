import pandas as pd, pathlib

ROOT = pathlib.Path("C:/AI/AlphaUltra")
fpath = ROOT / "data/gold/features_eng.parquet"
df = pd.read_parquet(fpath)
for col in ("tdnet_event_score", "news_sentiment"):
    if col not in df.columns:
        df[col] = 0.0
df.to_parquet(fpath, index=False)
print("[stub] tdnet_event_score/news_sentiment columns ensured")

