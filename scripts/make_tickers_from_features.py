#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import sys
from pathlib import Path
import pandas as pd


def main():
    if len(sys.argv) < 2:
        print("usage: make_tickers_from_features.py YYYY-MM-DD", file=sys.stderr)
        sys.exit(2)
    day = sys.argv[1]
    FEAT = Path("data/proc/features_tdnet/tdnet_event_features.parquet")
    if not FEAT.exists():
        print(f"features parquet not found: {FEAT}", file=sys.stderr)
        sys.exit(1)

    out_dir = Path("data/tmp"); out_dir.mkdir(parents=True, exist_ok=True)
    out1 = out_dir / f"tickers_{day.replace('-', '')}.csv"
    out_v2 = out_dir / "tickers_2014.csv"  # for v2 fetcher

    d = pd.read_parquet(FEAT, columns=["ticker","date"])
    d["date"] = pd.to_datetime(d["date"], errors="coerce")
    d = d.dropna(subset=["date"]).copy()
    w = d[d["date"].dt.date == pd.Timestamp(day).date()]["ticker"].astype(str)
    tick = sorted(x for x in w.unique() if re.match(r"^\d{4}\.T$", x))

    pd.Series(tick).to_csv(out1, index=False, header=False)
    pd.Series(tick).to_csv(out_v2, index=False, header=False)
    print({"tickers_day": len(tick), "out": str(out1), "out_v2": str(out_v2)})


if __name__ == "__main__":
    main()

