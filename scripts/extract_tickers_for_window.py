#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import sys
import unicodedata as ud
from pathlib import Path
import pandas as pd


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--include-etf", action="store_true", help="ETF/指数(13xx,15xx,16xx,17xx)を含める")
    a = ap.parse_args()

    feat = Path("data/proc/features_tdnet/tdnet_event_features.parquet")
    if not feat.exists():
        print({"error": "features_missing", "path": str(feat)})
        sys.exit(1)

    d = pd.read_parquet(feat, columns=["ticker", "date"]).dropna()
    d["date"] = pd.to_datetime(d["date"], errors="coerce")
    d = d.dropna(subset=["date"]).copy()
    w = d[(d["date"] >= a.start) & (d["date"] <= a.end)]["ticker"].astype(str)

    # Unicode 正規化（NFKC）→ ASCII 数字化
    def norm_ticker(s: str) -> str:
        s = ud.normalize('NFKC', s or '').strip().upper()
        return s
    w = w.map(norm_ticker)

    # 4桁.T かつ 1300-9999 のみ。ETF/指数(13xx,15xx,16xx,17xx)は既定で除外
    def is_equity(t: str) -> bool:
        m = re.fullmatch(r"(\d{4})\.T", t)
        if not m:
            return False
        c4 = m.group(1)
        n = int(c4)
        if n < 1300 or n > 9999:
            return False
        if not a.include_etf:
            if 1300 <= n <= 1399:
                return False
            if 1500 <= n <= 1799:
                return False
        return True

    tick = sorted({t for t in w if is_equity(t)})

    out_dir = Path("data/tmp"); out_dir.mkdir(parents=True, exist_ok=True)
    if a.start == a.end:
        tag = a.start.replace("-", "")
    elif a.start[:4] == a.end[:4] and a.start.endswith("-01-01") and a.end.endswith("-12-31"):
        tag = a.start[:4]
    else:
        tag = a.start.replace("-", "") + "_" + a.end.replace("-", "")
    out = out_dir / f"tickers_{tag}.csv"
    pd.Series(tick).to_csv(out, index=False, header=False, encoding="utf-8")
    head10 = tick[:10]
    print({"tickers": len(tick), "out": str(out), "head": head10})


if __name__ == "__main__":
    main()

