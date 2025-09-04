#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Align TDNET events to next trading day per ticker using searchsorted on the
standardized JP price panel, then join prices and emit a panel parquet.

Inputs
  data/proc/features_tdnet/tdnet_event_features.parquet
  data/proc/prices/jp_prices_std.parquet

Output
  data/proc/dataset/tdnet_panel.parquet

No tolerance beyond next-trading-day. Rows without a matched eff_date are dropped.
"""

from pathlib import Path
import json
import pandas as pd
from pandas.tseries.offsets import BDay


ROOT = Path(".").resolve()
FEAT = ROOT / "data/proc/features_tdnet/tdnet_event_features.parquet"
PX = ROOT / "data/proc/prices/jp_prices_std.parquet"
OUT = ROOT / "data/proc/dataset/tdnet_panel.parquet"


def searchsorted_next(dates: pd.Series, anchor: pd.Timestamp) -> pd.Timestamp | None:
    # dates must be sorted unique daily index (normalized)
    # return first date >= anchor
    if dates.empty:
        return None
    pos = dates.searchsorted(anchor, side="left")
    if pos >= len(dates):
        return None
    return dates.iloc[pos]


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if not FEAT.exists() or not PX.exists():
        print(json.dumps({
            "error": "missing_inputs",
            "features_exists": FEAT.exists(),
            "prices_exists": PX.exists(),
        }, ensure_ascii=False))
        return

    td = pd.read_parquet(FEAT)
    px = pd.read_parquet(PX)

    td["date"] = pd.to_datetime(td["date"], errors="coerce").dt.normalize()
    td = td.dropna(subset=["ticker", "date"]).sort_values(["ticker", "date"]).copy()
    px["date"] = pd.to_datetime(px["date"], errors="coerce").dt.normalize()
    px = px.dropna(subset=["ticker", "date", "adj_close"]).sort_values(["ticker", "date"]).copy()

    panels = []
    for tkr, ge in td.groupby("ticker", sort=True):
        gp = px[px["ticker"] == tkr]
        if gp.empty:
            continue
        dates = gp["date"].reset_index(drop=True)
        ge = ge.sort_values("date").copy()
        # eff_anchor is next business day (weekday) from event date
        anchors = (ge["date"] + BDay(1)).dt.normalize()
        eff_dates = []
        for a in anchors:
            eff_dates.append(searchsorted_next(dates, a))
        ge["eff_date"] = eff_dates
        ge = ge.dropna(subset=["eff_date"]).copy()
        merged = ge.merge(gp, left_on=["ticker", "eff_date"], right_on=["ticker", "date"], how="left", suffixes=("", "_px"))
        merged = merged.rename(columns={"date_x": "date"})
        keep_cols = [
            "ticker", "date", "eff_date", "event_cat", "tone_pos", "tone_neg", "tone_unc",
            "event_strength", "novelty", "adj_close", "volume"
        ] + [c for c in ge.columns if c.startswith("ev_")]
        merged = merged[keep_cols]
        panels.append(merged)

    panel = pd.concat(panels, ignore_index=True) if panels else pd.DataFrame(columns=[
        "ticker", "date", "eff_date", "event_cat", "tone_pos", "tone_neg", "tone_unc",
        "event_strength", "novelty", "adj_close", "volume"
    ])
    panel = panel.sort_values(["ticker", "date"]).reset_index(drop=True)
    panel.to_parquet(OUT, index=False)

    print(json.dumps({
        "panel_shape": [int(panel.shape[0]), int(panel.shape[1])],
        "tickers": int(panel["ticker"].nunique()) if not panel.empty else 0,
        "date_min": str(panel["date"].min().date()) if not panel.empty else None,
        "date_max": str(panel["date"].max().date()) if not panel.empty else None,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

