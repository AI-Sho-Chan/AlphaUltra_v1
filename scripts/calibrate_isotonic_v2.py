#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T7: Isotonic calibration and PPV>=target threshold search on OOF predictions.

Input:
  - reports/checks/tdnet_model_y_2x_oof.parquet (columns: y, p_raw, eff_date, ticker, date)

Output:
  - reports/checks/tdnet_model_y_2x_calib.json (thr_ppv80, ppv, coverage)
  - reports/calibrate_isotonic_v2.log
"""

from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression

ROOT = Path('.')
REPORTS = ROOT / 'reports'
CHECKS = ROOT / 'reports/checks'


def log_write(msg: str):
    REPORTS.mkdir(parents=True, exist_ok=True)
    with open(REPORTS / 'calibrate_isotonic_v2.log', 'a', encoding='utf-8') as f:
        f.write(msg.rstrip() + '\n')


def ppv_coverage(y: np.ndarray, p: np.ndarray, thresholds: np.ndarray) -> pd.DataFrame:
    rows = []
    for t in thresholds:
        mask = (p >= t)
        cov = float(mask.mean())
        if cov == 0.0:
            rows.append({'thr': float(t), 'ppv': None, 'coverage': 0.0}); continue
        ppv = float(y[mask].mean())
        rows.append({'thr': float(t), 'ppv': ppv, 'coverage': cov})
    return pd.DataFrame(rows)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--oof', default='reports/checks/tdnet_model_y_2x_oof.parquet')
    ap.add_argument('--ppv-target', type=float, default=0.8)
    args = ap.parse_args()

    CHECKS.mkdir(parents=True, exist_ok=True)
    df = pd.read_parquet(args.oof)
    df = df.dropna(subset=['p_raw'])
    y = df['y'].astype(int).values
    p = df['p_raw'].astype(float).values
    if len(p) == 0:
        out = {'ppv_target': float(args.ppv_target), 'thr_ppv80': 'none', 'ppv': None, 'coverage': 0.0, 'n_oof': 0}
        (CHECKS / 'tdnet_model_y_2x_calib.json').write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
        log_write(json.dumps(out, ensure_ascii=False))
        print(json.dumps(out, ensure_ascii=False))
        return

    # Fit isotonic on OOF (pragmatic for baseline)
    ir = IsotonicRegression(out_of_bounds='clip', y_min=0.0, y_max=1.0)
    p_cal = ir.fit_transform(p, y)

    # Build PPV-Coverage curve
    thr = np.linspace(0.0, 1.0, 201)
    curve = ppv_coverage(y, p_cal, thr)

    # Find minimal threshold achieving PPV>=target
    ok = curve.dropna(subset=['ppv'])
    ok = ok[ok['ppv'] >= float(args.ppv_target)]
    if ok.empty:
        thr_star = 'none'; ppv_star = None; cov_star = 0.0
    else:
        row = ok.sort_values(['thr','coverage']).iloc[0]
        thr_star = float(row['thr']); ppv_star = float(row['ppv']); cov_star = float(row['coverage'])

    out = {
        'ppv_target': float(args.ppv_target),
        'thr_ppv80': thr_star,
        'ppv': ppv_star,
        'coverage': cov_star,
        'n_oof': int(len(df))
    }
    (CHECKS / 'tdnet_model_y_2x_calib.json').write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    log_write(json.dumps(out, ensure_ascii=False))
    print(json.dumps(out, ensure_ascii=False))


if __name__ == '__main__':
    main()
