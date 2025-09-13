#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T5: Purged/Embargo CV scaffold for TDNET (2014 window)

Outputs
  - reports/cv_t5_y2x.json (legacy)
  - reports/cv_t5_y_2x_v2.json (when --mode q4_test or --out specified)
  - reports/t5_cv_setup.log

Notes
  - Uses eff_date (T+1) alignment from tdnet_panel.parquet
  - Liquidity filter (if data available): ADDV_3M >= 1e8 JPY, price >= 200 JPY
  - Cluster purge: correlation clusters over 60 trading days (fallback to naive prefix)
  - Baseline metrics only (random scores): AUC-ROC, AUC-PR, P@K
"""

from __future__ import annotations
import json, yaml, os, sys
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd


ROOT = Path('.')
PANEL = ROOT / 'data/proc/dataset/tdnet_panel.parquet'
LABELS = ROOT / 'data/proc/labels/targets.parquet'
PRICES = ROOT / 'data/proc/prices/jp_prices_std.parquet'
REPORTS = ROOT / 'reports'


def log(msg: str):
    REPORTS.mkdir(parents=True, exist_ok=True)
    with open(REPORTS / 't5_cv_setup.log', 'a', encoding='utf-8') as f:
        f.write(msg.strip() + '\n')


def last_trading_day_of_month(sessions: pd.DatetimeIndex) -> Dict[Tuple[int,int], pd.Timestamp]:
    out = {}
    for dt in sessions:
        key = (dt.year, dt.month)
        if key not in out or dt > out[key]:
            out[key] = dt
    return out


def build_quarter_test_windows(start: str, end: str, sessions: pd.DatetimeIndex) -> List[Tuple[pd.Timestamp, pd.Timestamp]]:
    sessions = pd.DatetimeIndex(pd.to_datetime(sessions)).tz_localize(None)
    s = pd.Timestamp(start); e = pd.Timestamp(end)
    sessions = sessions[(sessions>=s) & (sessions<=e)]
    if sessions.empty:
        return []
    ldom = last_trading_day_of_month(sessions)
    q_ends = [
        ldom.get((s.year,3)), ldom.get((s.year,6)), ldom.get((s.year,9)), ldom.get((s.year,12))
    ]
    q_starts = [
        sessions[0],
        (ldom.get((s.year,3)) + pd.Timedelta(days=1)) if ldom.get((s.year,3)) is not None else None,
        (ldom.get((s.year,6)) + pd.Timedelta(days=1)) if ldom.get((s.year,6)) is not None else None,
        (ldom.get((s.year,9)) + pd.Timedelta(days=1)) if ldom.get((s.year,9)) is not None else None,
    ]
    wins = []
    for qs, qe in zip(q_starts, q_ends):
        if qs is None or qe is None: continue
        # clip to sessions
        qs2 = sessions[sessions.searchsorted(qs, side='left')]
        qe2 = sessions[sessions.searchsorted(qe, side='right')-1]
        if qs2 <= qe2:
            wins.append((qs2, qe2))
    return wins


def split_equal_time_windows(start: str, end: str, sessions: pd.DatetimeIndex, n_splits: int) -> List[Tuple[pd.Timestamp, pd.Timestamp]]:
    sessions = pd.DatetimeIndex(pd.to_datetime(sessions)).tz_localize(None)
    s = pd.Timestamp(start); e = pd.Timestamp(end)
    sessions = sessions[(sessions>=s) & (sessions<=e)]
    if sessions.empty or n_splits<=0:
        return []
    blocks = np.array_split(sessions, n_splits)
    out = []
    for b in blocks:
        if len(b)==0: continue
        out.append((pd.Timestamp(b[0]), pd.Timestamp(b[-1])))
    return out


def ensure_sessions(start: str, end: str) -> pd.DatetimeIndex:
    # Try exchange_calendars (XTYO). Fallback to pandas bdate_range.
    try:
        import exchange_calendars as xcals
        cal = xcals.get_calendar('XTYO')
        sess = cal.sessions_in_range(pd.Timestamp(start), pd.Timestamp(end))
        return pd.DatetimeIndex(sess.tz_localize(None))
    except Exception:
        b = pd.bdate_range(start, end, freq='C')
        return pd.DatetimeIndex(b)


def compute_addv_and_price_at_eff(events: pd.DataFrame, px: pd.DataFrame) -> pd.DataFrame:
    # Prepare price features (ADDV_3M, price) as of eff_date (backward asof)
    px = px.copy()
    px['date'] = pd.to_datetime(px['date'], errors='coerce').dt.normalize()
    px = px.dropna(subset=['ticker','date','adj_close'])
    px['volume'] = px['volume'].fillna(0)
    px['addv'] = px['adj_close'] * px['volume']
    px = px.sort_values(['ticker','date'])
    px['addv_3m'] = px.groupby('ticker')['addv'].rolling(63,min_periods=20).mean().reset_index(level=0, drop=True)
    keep = px[['ticker','date','addv_3m','adj_close']].rename(columns={'adj_close':'px_close'})

    ev = events[['ticker','eff_date']].copy().rename(columns={'eff_date':'date'})
    outs = []
    for tkr, g in ev.groupby('ticker', sort=True):
        gp = keep[keep['ticker']==tkr][['date','addv_3m','px_close']].sort_values('date')
        if gp.empty:
            gg = g.copy(); gg['addv_3m']=np.nan; gg['px_close']=np.nan; outs.append(gg); continue
        mg = pd.merge_asof(g.sort_values('date'), gp, on='date', direction='backward', tolerance=pd.Timedelta('10D'))
        mg['ticker']=tkr
        outs.append(mg)
    aug = pd.concat(outs, ignore_index=True) if outs else pd.DataFrame(columns=['ticker','date','addv_3m','px_close'])
    aug = aug.rename(columns={'date':'eff_date'})
    if not aug.empty:
        aug = aug.drop_duplicates(['ticker','eff_date'])
    try:
        return events.merge(aug, on=['ticker','eff_date'], how='left', validate='m:1')
    except Exception:
        return events.merge(aug, on=['ticker','eff_date'], how='left')


def greedy_corr_clusters(px: pd.DataFrame, tickers: List[str], asof: pd.Timestamp, lookback_td: int) -> Dict[str,int]:
    # Build correlation matrix on recent returns and cluster greedily by high corr >= 0.7
    try:
        px = px.copy()
        px['date'] = pd.to_datetime(px['date'], errors='coerce').dt.normalize()
        asof = pd.Timestamp(asof)
        start = asof - pd.Timedelta(days=int(lookback_td*2))
        g = px[(px['date']<=asof) & (px['date']>=start) & (px['ticker'].isin(tickers))]
        if g.empty:
            return {t:i%16 for i,t in enumerate(sorted(set(tickers)))}
        pv = g.pivot(index='date', columns='ticker', values='adj_close').sort_index()
        rets = pv.pct_change().dropna(how='all')
        if rets.empty:
            return {t:i%16 for i,t in enumerate(sorted(set(tickers)))}
        rets = rets.fillna(0.0)
        corr = rets.corr().fillna(0.0)
        cols = list(corr.columns)
        unassigned = set(cols)
        labels: Dict[str,int] = {}
        cid = 0
        while unassigned:
            # pick seed with highest avg corr to others
            seed = max(unassigned, key=lambda t: float(corr.loc[t, list(unassigned)].mean()))
            members = {seed}
            # include members with strong corr to seed
            for t in list(unassigned):
                if float(corr.at[seed, t]) >= 0.7:
                    members.add(t)
            for t in members:
                labels[t]=cid
            unassigned -= members
            cid += 1
        # ensure every ticker present
        for t in tickers:
            labels.setdefault(t, cid); cid += 1
        return labels
    except Exception:
        return {t:i%16 for i,t in enumerate(sorted(set(tickers)))}


def mask_purged(dates: pd.Series, val_start: pd.Timestamp, val_end: pd.Timestamp, purge_days: int, embargo_days: int) -> pd.Series:
    left = val_start - pd.Timedelta(days=int(purge_days))
    right = val_end + pd.Timedelta(days=int(embargo_days))
    return (dates < left) | (dates > right)


def auc_roc_fast(y_true: np.ndarray, y_score: np.ndarray) -> float | None:
    y = np.asarray(y_true).astype(int)
    s = np.asarray(y_score).astype(float)
    n1 = int((y==1).sum()); n0 = int((y==0).sum())
    if n1==0 or n0==0:
        return None
    order = np.argsort(s)
    ranks = np.empty_like(order)
    ranks[order] = np.arange(1, len(s)+1)
    sum_ranks_pos = float(ranks[y==1].sum())
    auc = (sum_ranks_pos - n1*(n1+1)/2.0) / (n0*n1)
    return float(auc)


def average_precision(y_true: np.ndarray, y_score: np.ndarray) -> float | None:
    y = np.asarray(y_true).astype(int)
    s = np.asarray(y_score).astype(float)
    n1 = int((y==1).sum())
    if n1==0:
        return None
    idx = np.argsort(-s)
    ys = y[idx]
    cum_tp = np.cumsum(ys==1)
    prec = cum_tp / (np.arange(len(ys)) + 1)
    ap = float(prec[ys==1].mean()) if n1>0 else None
    return ap


def precision_at_k_abs(y_true: np.ndarray, y_score: np.ndarray, k_abs: int = 100) -> float | None:
    n = len(y_true)
    if n==0:
        return None
    k = min(int(k_abs), n)
    idx = np.argsort(-np.asarray(y_score))[:k]
    y = np.asarray(y_true)[idx]
    return float(np.mean(y)) if k>0 else None


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', default='configs/tdnet_2014.yaml')
    ap.add_argument('--label', default='y_2x')
    ap.add_argument('--folds', type=int, default=5)
    ap.add_argument('--purge', type=int, default=20)
    ap.add_argument('--embargo', type=int, default=5)
    ap.add_argument('--cluster', type=int, default=60, help='cluster lookback trading days (approx)')
    ap.add_argument('--topk', type=int, default=100, help='P@K absolute K for baseline')
    ap.add_argument('--train-start', default=None, help='override training data start date (eff_date >= this)')
    ap.add_argument('--liquidity', choices=['strict','loose'], default='strict')
    ap.add_argument('--mode', choices=['auto','equal','quarterly','q4_test'], default='auto')
    ap.add_argument('--out', default=None, help='override output JSON path')
    args = ap.parse_args()

    # Load config
    try:
        cfg = yaml.safe_load(Path(args.config).read_text(encoding='utf-8'))
    except Exception:
        cfg = {}
    paths = cfg.get('paths', {})
    start = str(cfg.get('params', {}).get('start_date') or '2014-01-01')
    end   = str(cfg.get('params', {}).get('end_date') or '2014-12-31')
    if args.train_start:
        start = str(args.train_start)

    # Input data
    if not PANEL.exists():
        log(f"panel missing: {PANEL}")
    if not LABELS.exists():
        log(f"labels missing: {LABELS}")
    if not PRICES.exists():
        log(f"prices missing: {PRICES}")

    panel = pd.read_parquet(PANEL) if PANEL.exists() else pd.DataFrame(columns=['ticker','date','eff_date'])
    labels= pd.read_parquet(LABELS) if LABELS.exists() else pd.DataFrame(columns=['ticker','date',args.label])
    px    = pd.read_parquet(PRICES) if PRICES.exists() else pd.DataFrame(columns=['ticker','date','adj_close','volume'])

    for df in (panel, labels):
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.normalize()
    if 'eff_date' in panel.columns:
        panel['eff_date'] = pd.to_datetime(panel['eff_date'], errors='coerce').dt.normalize()
    else:
        panel['eff_date'] = pd.to_datetime(panel['date'], errors='coerce').dt.normalize() + pd.tseries.offsets.BDay(1)
        panel['eff_date'] = pd.to_datetime(panel['eff_date']).dt.normalize()

    # Merge labels on (ticker,date)
    df = panel.merge(labels[['ticker','date',args.label]] if not labels.empty else panel.assign(**{args.label: np.nan})[['ticker','date',args.label]],
                     on=['ticker','date'], how='left')

    # Filter by window (on eff_date)
    # For q4_test, include training lookback from 2013-09-01
    if 'q4_test' in sys.argv:
        start = '2013-09-01'
    s = pd.Timestamp(start); e = pd.Timestamp(end)
    df = df[(df['eff_date']>=s) & (df['eff_date']<=e)].copy()

    # Liquidity features + filter (if available)
    df = compute_addv_and_price_at_eff(df, px) if not px.empty else df
    before_liq = len(df)
    liq_mask = pd.Series(True, index=df.index)
    if 'addv_3m' in df.columns and args.liquidity == 'strict':
        liq_mask &= (df['addv_3m'] >= 1e8)
    if 'px_close' in df.columns:
        liq_mask &= (df['px_close'] >= 200.0)
    df = df[liq_mask].copy()
    after_liq = len(df)
    log(f"liquidity filter: before={before_liq} after={after_liq}")

    # Sessions and fold windows
    sessions = ensure_sessions(start, end)
    q_wins = build_quarter_test_windows(start, end, sessions)

    mode = args.mode
    test_windows: List[Tuple[pd.Timestamp,pd.Timestamp]] = []
    if mode == 'q4_test':
        tstart = pd.Timestamp('2014-10-21')
        tend   = pd.Timestamp('2014-12-31')
        test_windows = [(tstart, tend)]
    elif mode == 'quarterly' or (mode=='auto' and args.folds==4 and len(q_wins)==4):
        test_windows = q_wins
        mode = 'quarterly'
    elif mode == 'equal' or mode == 'auto':
        test_windows = split_equal_time_windows(start, end, sessions, max(1, int(args.folds)))
        mode = 'equal_windows'
    log(f"cv_mode={mode} folds={len(test_windows)}")

    # Clusters
    tickers = sorted(df['ticker'].astype(str).unique().tolist())
    if 'cluster_id' in df.columns:
        clmap = {t:int(x) for t,x in df[['ticker','cluster_id']].dropna().drop_duplicates().itertuples(index=False)}
    else:
        clmap = greedy_corr_clusters(px, tickers, pd.Timestamp(start) - pd.Timedelta(days=1), int(args.cluster)) if not px.empty else {t:i%16 for i,t in enumerate(tickers)}
    df['cluster_id'] = df['ticker'].map(clmap)

    # Build folds with purge/embargo + cluster purge
    folds_meta = []
    oof_scores = []
    oof_labels = []
    np.random.seed(42)
    for i,(tstart,tend) in enumerate(test_windows, start=1):
        va_mask = (df['eff_date']>=tstart) & (df['eff_date']<=tend)
        tr_mask = ~va_mask
        tr_mask = tr_mask & mask_purged(df['eff_date'], tstart, tend, int(args.purge), int(args.embargo))

        # cluster purge within purge/embargo band
        test_clusters = set(df.loc[va_mask, 'cluster_id'].dropna().astype(int).tolist())
        if test_clusters:
            left = tstart - pd.Timedelta(days=int(args.purge))
            right = tend + pd.Timedelta(days=int(args.embargo))
            same_cluster = df['cluster_id'].isin(test_clusters)
            within_band = (df['eff_date']>=left) & (df['eff_date']<=right)
            tr_mask = tr_mask & ~(same_cluster & within_band)

        n_tr = int(tr_mask.sum()); n_va = int(va_mask.sum())
        pos_tr = int(df.loc[tr_mask, args.label].fillna(0).astype(int).sum()) if n_tr>0 and args.label in df.columns else 0
        pos_va = int(df.loc[va_mask, args.label].fillna(0).astype(int).sum()) if n_va>0 and args.label in df.columns else 0
        folds_meta.append({
            'fold': i,
            'train_start': str(df.loc[tr_mask, 'eff_date'].min().date()) if n_tr>0 else None,
            'train_end':   str(df.loc[tr_mask, 'eff_date'].max().date()) if n_tr>0 else None,
            'test_start':  str(pd.Timestamp(tstart).date()),
            'test_end':    str(pd.Timestamp(tend).date()),
            'n_train': n_tr,
            'n_test': n_va,
            'pos_train': pos_tr,
            'pos_test': pos_va,
        })

        # Baseline random scores for OOF
        if n_va>0 and args.label in df.columns:
            y_va = df.loc[va_mask, args.label].fillna(0).astype(int).values
            s_va = np.random.RandomState(42 + i).rand(n_va)
            oof_labels.append(y_va)
            oof_scores.append(s_va)

    # Concatenate OOF and compute metrics
    metrics = {'auc_roc': None, 'auc_pr': None, 'p_at_k': None, 'k': int(args.topk)}
    if oof_labels and oof_scores:
        y_all = np.concatenate(oof_labels)
        s_all = np.concatenate(oof_scores)
        auc = auc_roc_fast(y_all, s_all)
        ap = average_precision(y_all, s_all)
        pk = precision_at_k_abs(y_all, s_all, k_abs=int(args.topk))
        metrics = {
            'auc_roc': None if auc is None else float(auc),
            'auc_pr': None if ap is None else float(ap),
            'p_at_k': None if pk is None else float(pk),
            'k': int(args.topk),
        }

    # Leak checks
    leak = {'train_test_overlap': 0, 'adjacent_overlap': {}}
    # train/test overlap is inherently 0 by masks, but we check accidental intersections on keys
    try:
        for i,(tstart,tend) in enumerate(test_windows, start=1):
            va_keys = set(df.loc[(df['eff_date']>=tstart)&(df['eff_date']<=tend), ['ticker','eff_date']].itertuples(index=False, name=None))
            tr_keys = set(df.loc[mask_purged(df['eff_date'], tstart, tend, int(args.purge), int(args.embargo)), ['ticker','eff_date']].itertuples(index=False, name=None))
            inter = va_keys & tr_keys
            leak['train_test_overlap'] += len(inter)
        for i in range(len(test_windows)-1):
            a = test_windows[i]; b = test_windows[i+1]
            keys_a = set(df.loc[(df['eff_date']>=a[0])&(df['eff_date']<=a[1]), ['ticker','eff_date']].itertuples(index=False, name=None))
            keys_b = set(df.loc[(df['eff_date']>=b[0])&(df['eff_date']<=b[1]), ['ticker','eff_date']].itertuples(index=False, name=None))
            leak['adjacent_overlap'][f'fold{i+1}_{i+2}'] = len(keys_a & keys_b)
    except Exception:
        pass

    # Clusters summary (sizes only)
    cl_sizes = pd.Series(df['cluster_id'].dropna().astype(int)).value_counts().sort_index().to_dict()
    clusters_obj = {
        'n_clusters': int(len(set(clmap.values()))) if clmap else 0,
        'sizes': {str(k): int(v) for k,v in cl_sizes.items()}
    }

    out = {
        'folds': folds_meta,
        'purge_days': int(args.purge),
        'embargo_days': int(args.embargo),
        'cv_mode': mode,
        'clusters': clusters_obj,
        'metrics_baseline': metrics,
        'leak_check': leak,
        'rows_total': int(len(df)),
        'liquidity': {
            'applied': bool('addv_3m' in df.columns or 'px_close' in df.columns),
            'stats': {'before': int(before_liq), 'after': int(after_liq), 'addv_min': 1e8, 'price_min': 200.0}
        }
    }

    REPORTS.mkdir(parents=True, exist_ok=True)
    out_name = args.out
    if not out_name:
        out_path = REPORTS / ('cv_t5_y2x.json' if mode != 'q4_test' else 'cv_t5_y_2x_v2.json')
    else:
        # if user provided a path with directories, respect it as-is
        op = Path(out_name)
        out_path = op if (op.is_absolute() or (op.parent and str(op.parent) not in ('.',''))) else (REPORTS / out_name)
        out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'folds': len(folds_meta), 'mode': mode, 'rows': int(len(df)), 'p_at_k': metrics['p_at_k'], 'out': str(out_path)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
