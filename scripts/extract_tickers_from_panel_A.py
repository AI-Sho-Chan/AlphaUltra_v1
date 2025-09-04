# -*- coding: utf-8 -*-
import pandas as pd
from pathlib import Path

PANEL = Path("data/proc/dataset/tdnet_panel.parquet")
OUT   = Path("data/tmp/tickers_A.csv"); OUT.parent.mkdir(parents=True, exist_ok=True)

df = pd.read_parquet(PANEL, columns=["ticker","date"])
df["date"] = pd.to_datetime(df["date"])
win = df[(df["date"] >= "2013-11-10") & (df["date"] <= "2013-11-20")]

tick = sorted(win["ticker"].astype(str).unique())
pd.Series(tick).to_csv(OUT, index=False, header=False)

print({"tickers_A": len(tick), "out": str(OUT)})
