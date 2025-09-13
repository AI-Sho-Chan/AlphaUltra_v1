#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Normalize J-Quants quarterly financials into a single parquet for as-of joins.

Input:  data/raw/jquants/fin/*.parquet  (columns: code,ticker,period_end,q_flag,fs_type,metrics,json,source)
Output: data/proc/fin/fin_quarter_norm.parquet
  columns: code,ticker,period_end,disclosed_date,q_flag,fs_type,
           sales,op_profit,ord_profit,net_profit,assets,equity,eps,
           opm,roe,roa,self_cap, sales_yoy, op_yoy, source

Notes
- Keeps only quarterly rows (q_flag in {1Q,2Q,3Q,4Q})
- disclosed_date parsed from metrics keys (DisclosedDate, etc.)
- Computes simple YoY by quarter flag within code (same q_flag previous year)
- Writes a one-line JSON log to reports/fin_load_asof.log
"""

from __future__ import annotations
import json
from pathlib import Path
import pandas as pd


RAW = Path('data/raw/jquants/fin')
OUT = Path('data/proc/fin'); OUT.mkdir(parents=True, exist_ok=True)
REPD = Path('reports'); REPD.mkdir(parents=True, exist_ok=True)


def to_num(x):
    try:
        if x is None or x == '':
            return None
        return float(x)
    except Exception:
        return None


def parse_metrics_to_cols(mstr: str | dict) -> dict:
    if isinstance(mstr, dict):
        m = mstr
    else:
        try:
            m = json.loads(mstr or '{}')
        except Exception:
            m = {}
    # extract fields
    out = {}
    # disclosed date
    dd = m.get('DisclosedDate') or m.get('DisclosureDate') or m.get('Date') or ''
    try:
        out['disclosed_date'] = pd.to_datetime(dd, errors='coerce').normalize()
    except Exception:
        out['disclosed_date'] = pd.NaT
    # numeric KPIs
    out['sales']        = to_num(m.get('NetSales') or m.get('Revenue'))
    out['op_profit']    = to_num(m.get('OperatingProfit'))
    out['ord_profit']   = to_num(m.get('OrdinaryProfit'))
    out['net_profit']   = to_num(m.get('Profit') or m.get('NetIncome'))
    out['assets']       = to_num(m.get('TotalAssets') or m.get('Assets'))
    out['equity']       = to_num(m.get('Equity') or m.get('NetAssets'))
    out['eps']          = to_num(m.get('EarningsPerShare') or m.get('EPS'))
    return out


def compute_ratios(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d['opm'] = d['op_profit'] / d['sales']
    d['roe'] = d['net_profit'] / d['equity']
    d['roa'] = d['net_profit'] / d['assets']
    d['self_cap'] = d['equity'] / d['assets']
    return d


def compute_yoy(df: pd.DataFrame) -> pd.DataFrame:
    # YoY by same quarter flag
    d = df.sort_values(['code', 'q_flag', 'period_end']).copy()
    d['year'] = pd.to_datetime(d['period_end']).dt.year
    for col, newc in [('sales', 'sales_yoy'), ('op_profit', 'op_yoy')]:
        d[newc] = pd.NA
    for (code, q), g in d.groupby(['code', 'q_flag'], sort=False):
        g = g.sort_values('period_end')
        prev = g[[col for col in ['sales','op_profit']]].shift(4)  # approx annual backshift (quarterly series)
        idx = g.index
        d.loc[idx, 'sales_yoy'] = g['sales'].values / prev['sales'].values - 1
        d.loc[idx, 'op_yoy']    = g['op_profit'].values / prev['op_profit'].values - 1
    d = d.drop(columns=['year'])
    return d


def main():
    records = []
    for fp in sorted(RAW.glob('*.parquet')):
        try:
            q = pd.read_parquet(fp)
        except Exception:
            continue
        if q.empty:
            continue
        # Keep only quarterly rows
        qf = q.get('q_flag')
        if qf is not None:
            q = q[q['q_flag'].astype(str).str.upper().str.contains('Q', na=False)].copy()
        if q.empty:
            continue
        # basic columns
        base = q[['code','ticker','period_end','q_flag','fs_type','metrics','source']].copy()
        # metrics parsing
        met = base['metrics'].apply(parse_metrics_to_cols).apply(pd.Series)
        d = pd.concat([base.drop(columns=['metrics']), met], axis=1)
        # normalize dtypes
        d['period_end'] = pd.to_datetime(d['period_end'], errors='coerce').dt.normalize()
        d['disclosed_date'] = pd.to_datetime(d['disclosed_date'], errors='coerce').dt.normalize()
        records.append(d)

    if not records:
        print(json.dumps({'rows':0}, ensure_ascii=False)); return

    df = pd.concat(records, ignore_index=True)
    df = compute_ratios(df)
    df = compute_yoy(df)
    # final order
    keep = ['code','ticker','period_end','disclosed_date','q_flag','fs_type',
            'sales','op_profit','ord_profit','net_profit','assets','equity','eps',
            'opm','roe','roa','self_cap','sales_yoy','op_yoy','source']
    for c in keep:
        if c not in df.columns:
            df[c] = pd.NA
    df = df[keep].dropna(subset=['ticker','period_end']).drop_duplicates(['ticker','period_end','fs_type','q_flag'])
    outp = OUT / 'fin_quarter_norm.parquet'
    df.to_parquet(outp, index=False)
    log = {'rows': int(len(df)), 'tickers': int(df['ticker'].nunique()),
           'date_min': str(df['period_end'].min().date()), 'date_max': str(df['period_end'].max().date())}
    print(json.dumps(log, ensure_ascii=False))
    (REPD / 'fin_load_asof.log').write_text(json.dumps(log, ensure_ascii=False)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()

