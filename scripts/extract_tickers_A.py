# -*- coding: utf-8 -*-
import re, pandas as pd
from pathlib import Path

PARQ = Path("data/proc/features_tdnet/tdnet_event_features.parquet")
OUT  = Path("data/tmp/tickers_A.csv"); OUT.parent.mkdir(parents=True, exist_ok=True)

START = "2013-11-10"; END = "2013-11-20"

df = pd.read_parquet(PARQ)
df["date"] = pd.to_datetime(df["date"])
win = df[(df["date"] >= START) & (df["date"] <= END)]
tickers = sorted(t for t in win["ticker"].astype(str).unique() if re.match(r"^\d{4}\.T$", t))
pd.Series(tickers).to_csv(OUT, index=False, header=False)
print({"tickers_A": len(tickers), "out": str(OUT)})
