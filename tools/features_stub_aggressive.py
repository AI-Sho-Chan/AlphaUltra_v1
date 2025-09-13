import pandas as pd, pathlib

ROOT = pathlib.Path(r"C:\AI\AlphaUltra")
fp = ROOT / "data/gold/features_eng.parquet"

df = pd.read_parquet(fp)

def ensure(col):
    if col not in df.columns:
        df[col] = 0.0

# Try to compute a simple momentum-like delta for zscore_scs
if {"ticker","date","zscore_scs"}.issubset(df.columns):
    try:
        df = df.sort_values(["ticker","date"])  # stable order
        df["scs_delta"] = df.groupby("ticker")["zscore_scs"].diff().fillna(0.0)
    except Exception:
        ensure("scs_delta")
else:
    ensure("scs_delta")

# novelty score as absolute delta
if "scs_delta" in df.columns:
    df["novelty_score"] = df["scs_delta"].abs()
else:
    ensure("novelty_score")

# Ensure expected stub columns exist for downstream usage
for c in ["tdnet_event_score","news_sentiment","vol_bucket","zscore_scs","zscore_sent"]:
    ensure(c)

df.to_parquet(fp)
print("[stub-aggr] ensured scs_delta/novelty_score")

