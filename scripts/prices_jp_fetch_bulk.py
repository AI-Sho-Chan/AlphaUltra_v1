#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fetch JP prices for all tickers present in features_tdnet/tdnet_event_features.parquet.
Stooq first (TICKER.JP), then Yahoo Finance fallback.

Saves per-ticker raw parquet to data/raw/prices/<ticker>.parquet with columns:
  date, adj_close, volume

After fetching, calls scripts/price_std_build.py to materialize
  data/proc/prices/jp_prices_std.parquet
"""

from pathlib import Path
import time
import sys
import pandas as pd
import pandas_datareader.data as pdr
import yfinance as yf
import subprocess


ROOT = Path(".").resolve()
RAW_PRICES = ROOT / "data/raw/prices"
FEAT_PATH = ROOT / "data/proc/features_tdnet/tdnet_event_features.parquet"


def dl_stooq(ticker: str, start: str = "2008-01-01") -> pd.DataFrame | None:
    sym = ticker.upper().replace(".T", ".JP")
    try:
        df = pdr.DataReader(sym, "stooq", start=start)
        if df is None or df.empty:
            return None
        df = df.sort_index()
        out = df[["Close", "Volume"]].rename(columns={"Close": "adj_close", "Volume": "volume"})
        out = out.reset_index().rename(columns={"Date": "date"})
        out["date"] = pd.to_datetime(out["date"]).dt.normalize()
        return out
    except Exception:
        return None


def dl_yf(ticker: str, start: str = "2008-01-01") -> pd.DataFrame | None:
    try:
        d = yf.download(ticker, start=start, auto_adjust=True, progress=False, threads=False)
        if d is None or d.empty:
            return None
        d = d[["Close", "Volume"]].rename(columns={"Close": "adj_close", "Volume": "volume"})
        d = d.reset_index().rename(columns={"Date": "date"})
        d["date"] = pd.to_datetime(d["date"]).dt.normalize()
        return d
    except Exception:
        return None


def main():
    RAW_PRICES.mkdir(parents=True, exist_ok=True)
    if not FEAT_PATH.exists():
        print(f"[prices_jp_fetch] features missing: {FEAT_PATH}")
        sys.exit(0)

    feat = pd.read_parquet(FEAT_PATH)
    tickers = sorted({t for t in feat.get("ticker", pd.Series([], dtype=str)).astype(str).str.upper().tolist() if t.endswith(".T")})
    print(f"[prices_jp_fetch] tickers={len(tickers)}")

    ok = 0
    for i, t in enumerate(tickers, start=1):
        out = RAW_PRICES / f"{t}.parquet"
        if out.exists():
            continue
        df = dl_stooq(t)
        src = "stooq"
        if df is None or df.empty:
            df = dl_yf(t)
            src = "yf"
        if df is None or df.empty:
            print(f"[prices_jp_fetch] fail {t}")
            continue
        df.to_parquet(out, index=False)
        ok += 1
        if i % 20 == 0:
            print(f"[prices_jp_fetch] {i}/{len(tickers)} saved (last={t}, src={src})")
        time.sleep(0.25)

    # Build standardized parquet
    try:
        subprocess.run([sys.executable, str(ROOT / "scripts/price_std_build.py")], check=False)
    except Exception:
        pass
    print(f"[prices_jp_fetch] done ok={ok}")


if __name__ == "__main__":
    main()

