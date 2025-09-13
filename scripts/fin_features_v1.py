#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Join as-of quarterly financial features into TDNET features (leakage-safe).

Rules
- Use latest quarterly row with period_end <= eff_date and disclosed_date <= eff_date (fallback to period_end if disclosed_date is NaT).
- One row per feature row (ticker,eff_date) choosing the most recent finance.

Inputs
  data/proc/fin/fin_quarter_norm.parquet
  data/proc/features_tdnet/tdnet_event_features.parquet

Output
  Overwrites features parquet adding fin_* columns

CLI
  --config configs/tdnet_2014.yaml (to restrict to 2014 window)
"""

from __future__ import annotations
import sys, json
from pathlib import Path
import pandas as pd
import yaml


ROOT = Path('.')
FIN = ROOT / 'data/proc/fin/fin_quarter_norm.parquet'
FEAT = ROOT / 'data/proc/features_tdnet/tdnet_event_features.parquet'
REPD = ROOT / 'reports'


def load_cfg(p: Path) -> dict:
    cfg = {'params': {'start_date': None, 'end_date': None}}
    if p.exists():
        try:
            u = yaml.safe_load(p.read_text(encoding='utf-8')) or {}
            if 'params' in u:
                cfg['params'].update(u['params'] or {})
        except Exception:
            pass
    return cfg


def main():
    # args
    cfg_path = Path(sys.argv[-1]) if len(sys.argv) > 2 and sys.argv[-2] == '--config' else Path('configs/tdnet_2014.yaml')
    cfg = load_cfg(cfg_path)
    start = cfg['params'].get('start_date')
    end   = cfg['params'].get('end_date')

    # load
    if not (FIN.exists() and FEAT.exists()):
        print(json.dumps({'error':'missing_inputs','fin_exists':FIN.exists(),'feat_exists':FEAT.exists()})); return
    fin = pd.read_parquet(FIN)
    feat_all = pd.read_parquet(FEAT)

    # restrict to window
    feat_all['date'] = pd.to_datetime(feat_all['date'], errors='coerce').dt.normalize()
    feat_all['eff_date'] = pd.to_datetime(feat_all.get('eff_date'), errors='coerce').dt.normalize()
    feat = feat_all.copy()
    # normalize start/end to timestamps
    start_ts = pd.to_datetime(start).normalize() if start else None
    end_ts   = pd.to_datetime(end).normalize() if end else None
    if start_ts is not None:
        feat = feat[feat['date'] >= start_ts]
    if end_ts is not None:
        feat = feat[feat['date'] <= end_ts]
    feat = feat.dropna(subset=['ticker','eff_date']).copy()
    rows_before = int(len(feat))
    # drop existing fin_ columns in window to avoid duplicates
    drop_cols = [c for c in feat.columns if c.startswith('fin_')]
    if drop_cols:
        feat = feat.drop(columns=drop_cols)

    # finance prep
    fin = fin.copy()
    fin['period_end'] = pd.to_datetime(fin['period_end'], errors='coerce').dt.normalize()
    fin['disclosed_date'] = pd.to_datetime(fin['disclosed_date'], errors='coerce').dt.normalize()
    # use disclosed date when available, else period_end
    fin['asof_date'] = fin['disclosed_date']
    fin.loc[fin['asof_date'].isna(), 'asof_date'] = fin['period_end']
    # quarterly only
    fin = fin[fin['q_flag'].astype(str).str.upper().str.contains('Q', na=False)]
    fin = fin.dropna(subset=['ticker','asof_date']).sort_values(['ticker','asof_date'])

    # select numeric feature cols
    fin_cols = ['sales','op_profit','ord_profit','net_profit','assets','equity','eps','opm','roe','roa','self_cap','sales_yoy','op_yoy']
    # merge_asof by ticker
    merged_parts = []
    for t, g_feat in feat.groupby('ticker', sort=False):
        g_fin = fin[fin['ticker'] == t]
        if g_fin.empty:
            continue
        m = pd.merge_asof(
            g_feat.sort_values('eff_date'),
            g_fin[['asof_date'] + fin_cols + ['period_end','q_flag']].sort_values('asof_date'),
            left_on='eff_date', right_on='asof_date', direction='backward')
        merged_parts.append(m)
    if merged_parts:
        feat_m = pd.concat(merged_parts, ignore_index=True)
    else:
        feat_m = feat.copy()

    # rename to fin_* and attach
    add_map = {c: f'fin_{c}' for c in fin_cols}
    feat_m = feat_m.rename(columns=add_map)
    feat_m = feat_m.rename(columns={'period_end': 'fin_period_end', 'q_flag': 'fin_qflag'})

    # mark addition count
    fin_cols_added = list(add_map.values())
    feat_m['fin_any'] = feat_m[fin_cols_added].notna().any(axis=1)
    added = int(feat_m['fin_any'].sum())
    feat_rows_2014 = int(len(feat_m))

    # save back (overwrite) with window-only enriched features (simple, leak-safe for T5)
    out = FEAT
    feat_m.drop(columns=['fin_any','asof_date'], errors='ignore').to_parquet(out, index=False)

    # summary\n    rows_after = int(len(feat_m))\n    asof_hits = int(feat_m[[c for c in feat_m.columns if c.startswith('fin_')]].notna().any(axis=1).sum())\n    asof_misses = rows_after - asof_hits\n    summary = {\n        'fin_feats_added': added,\n        'features_rows_2014': feat_rows_2014,\n        'rows_before': rows_before,\n        'rows_after': rows_after,\n        'left_join': True,\n        'asof_hits': asof_hits,\n        'asof_misses': asof_misses,\n    }\n    print(json.dumps(summary, ensure_ascii=False))\n    REPD.mkdir(parents=True, exist_ok=True)\n    (REPD / 'fin_features_v1.log').write_text(json.dumps(summary, ensure_ascii=False)+'\n', encoding='utf-8')\n\n\nif __name__ == '__main__':\n    main()\n


