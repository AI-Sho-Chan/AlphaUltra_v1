#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build dual TDNET panels for 2014 scope:
 - REAL: prices where source != 'bootstrap'
 - FULL: all prices (REAL + bootstrap)

Writes:
  data/proc/dataset/tdnet_panel_real.parquet
  data/proc/dataset/tdnet_panel_full.parquet

Also writes health/log summaries under reports/.
"""

from __future__ import annotations
from pathlib import Path
import argparse, json, yaml
import pandas as pd
from pandas.tseries.offsets import BDay


ROOT = Path('.')
FEAT = ROOT / 'data/proc/features_tdnet/tdnet_event_features.parquet'
PX   = ROOT / 'data/proc/prices/jp_prices_std.parquet'
OUTD = ROOT / 'data/proc/dataset'; OUTD.mkdir(parents=True, exist_ok=True)
REPD = ROOT / 'reports'; REPD.mkdir(parents=True, exist_ok=True)
CFG_2014 = ROOT / 'configs/tdnet_2014.yaml'


def searchsorted_next(dates: pd.Series, anchor: pd.Timestamp) -> pd.Timestamp | None:
    if dates.empty:
        return None
    pos = dates.searchsorted(anchor, side='left')
    if pos >= len(dates):
        return None
    return dates.iloc[pos]


def build_panel(mode: str, start: str, end: str) -> dict:
    assert mode in {'real','full'}
    if not (FEAT.exists() and PX.exists()):
        info = {"error":"missing_inputs","features_exists": FEAT.exists(),"prices_exists": PX.exists()}
        print(json.dumps(info, ensure_ascii=False)); return info

    td = pd.read_parquet(FEAT)
    px = pd.read_parquet(PX)

    # Filter price source
    if mode == 'real':
        px = px[px.get('source').fillna('unknown') != 'bootstrap'].copy()

    # Normalize dates
    td['date'] = pd.to_datetime(td['date'], errors='coerce').dt.normalize()
    px['date'] = pd.to_datetime(px['date'], errors='coerce').dt.normalize()
    # Restrict to requested window (defaults provided by CLI/2014 config)
    # ensure start/end are parsed as timestamps
    start_ts = pd.to_datetime(start).normalize() if start else None
    end_ts   = pd.to_datetime(end).normalize() if end else None
    if start_ts is not None:
        td = td[td['date'] >= start_ts]
        px = px[px['date'] >= start_ts]
    if end_ts is not None:
        td = td[td['date'] <= end_ts]
        px = px[px['date'] <= end_ts]
    td = td.dropna(subset=['ticker','date']).sort_values(['ticker','date']).copy()
    px = px.dropna(subset=['ticker','date','adj_close']).sort_values(['ticker','date']).copy()

    panels = []
    for tkr, ge in td.groupby('ticker', sort=True):
        gp = px[px['ticker'] == tkr]
        if gp.empty:
            continue
        dates = gp['date'].reset_index(drop=True)
        ge = ge.sort_values('date').copy()
        # Next business day then align to next available trading day
        anchors = (ge['date'] + BDay(1)).dt.normalize()
        eff_dates = []
        for a in anchors:
            eff_dates.append(searchsorted_next(dates, a))
        ge['eff_date'] = eff_dates
        ge = ge.dropna(subset=['eff_date']).copy()
        merged = ge.merge(gp, left_on=['ticker','eff_date'], right_on=['ticker','date'], how='left', suffixes=("","_px"))
        merged = merged.rename(columns={'date_x':'date'})
        panels.append(merged)

    panel = pd.concat(panels, ignore_index=True) if panels else pd.DataFrame(columns=['ticker','date','eff_date'])
    panel = panel.sort_values(['ticker','date']).reset_index(drop=True)

    out_path = OUTD / ("tdnet_panel_real.parquet" if mode=='real' else "tdnet_panel_full.parquet")
    panel.to_parquet(out_path, index=False)

    # coverage summary
    cov = float(panel['adj_close'].notna().mean()) if len(panel) else 0.0
    feat_rows = int(len(td))
    feat_min  = str(td['date'].min().date()) if feat_rows else None
    feat_max  = str(td['date'].max().date()) if feat_rows else None
    info = {
        'mode': mode,
        'panel_shape': [int(panel.shape[0]), int(panel.shape[1])],
        'tickers': int(panel['ticker'].nunique()) if not panel.empty else 0,
        'price_coverage': cov,
        'date_min': str(panel['date'].min().date()) if not panel.empty else None,
        'date_max': str(panel['date'].max().date()) if not panel.empty else None,
        'out': str(out_path),
        'features_rows_used': feat_rows,
        'features_date_min': feat_min,
        'features_date_max': feat_max,
        'window': {'start': str(start_ts.date()) if start_ts is not None else None,
                   'end':   str(end_ts.date()) if end_ts is not None else None},
    }

    # logs
    (REPD / (f'tdnet_align_next_trading_{mode}.log')).write_text(json.dumps(info, ensure_ascii=False)+"\n", encoding='utf-8')
    (REPD / (f'healthcheck_tdnet_fast_v2_{mode}.log')).write_text(json.dumps(info, ensure_ascii=False)+"\n", encoding='utf-8')
    print(json.dumps(info, ensure_ascii=False))
    return info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', required=True, choices=['real','full'])
    ap.add_argument('--start', default=None)
    ap.add_argument('--end', default=None)
    a = ap.parse_args()

    start = a.start; end = a.end
    # if not provided, load from 2014 config
    if (start is None or end is None) and CFG_2014.exists():
        try:
            with CFG_2014.open('r', encoding='utf-8') as f:
                cfg = yaml.safe_load(f) or {}
            params = (cfg.get('params') or {})
            start = start or params.get('start_date')
            end   = end   or params.get('end_date')
        except Exception:
            pass
    build_panel(a.mode, start, end)


if __name__ == '__main__':
    main()
