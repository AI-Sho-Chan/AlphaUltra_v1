#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Report REAL vs FULL 2014 summary and bootstrap share in prices.

Outputs one JSON line:
{"real":{"rows":...,"coverage":...,"tickers":...},
 "full":{"rows":...,"coverage":...,"tickers":...},
 "bootstrap_share_in_prices": ...}
"""

from __future__ import annotations
import json
import pandas as pd
from pathlib import Path


ROOT = Path('.')
PANEL_REAL = ROOT / 'data/proc/dataset/tdnet_panel_real.parquet'
PANEL_FULL = ROOT / 'data/proc/dataset/tdnet_panel_full.parquet'
PX_STD      = ROOT / 'data/proc/prices/jp_prices_std.parquet'


def summarize_panel_2014(path: Path) -> dict:
    if not path.exists():
        return {"rows": 0, "coverage": 0.0, "tickers": 0}
    df = pd.read_parquet(path)
    df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.normalize()
    df = df[(df['date'] >= '2014-01-01') & (df['date'] <= '2014-12-31')]
    rows = int(len(df))
    cov = float(df['adj_close'].notna().mean()) if rows else 0.0
    tks = int(df['ticker'].nunique()) if rows else 0
    return {"rows": rows, "coverage": cov, "tickers": tks}


def bootstrap_share_in_prices_2014(px_path: Path) -> float:
    if not px_path.exists():
        return 0.0
    px = pd.read_parquet(px_path, columns=['date','source'])
    px['date'] = pd.to_datetime(px['date'], errors='coerce').dt.normalize()
    px = px[(px['date'] >= '2014-01-01') & (px['date'] <= '2014-12-31')]
    if px.empty:
        return 0.0
    return float((px['source'] == 'bootstrap').mean())


def main():
    real = summarize_panel_2014(PANEL_REAL)
    full = summarize_panel_2014(PANEL_FULL)
    share = bootstrap_share_in_prices_2014(PX_STD)
    out = {"real": real, "full": full, "bootstrap_share_in_prices": share}
    print(json.dumps(out, ensure_ascii=False))


if __name__ == '__main__':
    main()

