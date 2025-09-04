#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fast healthcheck for TDNET panel coverage.

Reads:
  data/proc/dataset/tdnet_panel.parquet
  data/proc/prices/jp_prices_std.parquet (for suffix-tolerant coverage if needed)

Prints JSON to stdout:
  { panel_shape, tickers, price_coverage, date_min, date_max }
"""

from pathlib import Path
import json
import pandas as pd


ROOT = Path(".").resolve()
PANEL = ROOT / "data/proc/dataset/tdnet_panel.parquet"
PX = ROOT / "data/proc/prices/jp_prices_std.parquet"


def coverage_from_panel(panel: pd.DataFrame) -> float:
    # tolerant to suffixes
    for c in ("adj_close", "adj_close_px", "adj_close_x", "adj_close_y"):
        if c in panel.columns:
            return float(panel[c].notna().mean()) if len(panel) else 0.0
    return 0.0


def main():
    if not PANEL.exists():
        print(json.dumps({
            "panel_shape": [0, 0],
            "tickers": 0,
            "price_coverage": 0.0,
            "date_min": None,
            "date_max": None,
            "note": "panel missing",
        }, ensure_ascii=False))
        return

    panel = pd.read_parquet(PANEL)
    cov = coverage_from_panel(panel)
    if cov == 0.0 and PX.exists():
        try:
            px = pd.read_parquet(PX)[["ticker", "date", "adj_close"]]
            panel_dates = panel[["ticker", "eff_date"]].rename(columns={"eff_date": "date"})
            m = panel_dates.merge(px, on=["ticker", "date"], how="left")
            cov = float(m["adj_close"].notna().mean()) if len(m) else 0.0
        except Exception:
            pass

    info = {
        "panel_shape": [int(panel.shape[0]), int(panel.shape[1])],
        "tickers": int(panel["ticker"].nunique()) if not panel.empty else 0,
        "price_coverage": cov,
        "date_min": str(panel["date"].min().date()) if not panel.empty else None,
        "date_max": str(panel["date"].max().date()) if not panel.empty else None,
    }
    print(json.dumps(info, ensure_ascii=False))


if __name__ == "__main__":
    main()

