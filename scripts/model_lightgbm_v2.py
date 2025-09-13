#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T6: LightGBM baseline using T5 folds (purged/embargo, 2014 window)

Inputs:
  - configs/tdnet_2014.yaml (for window)
  - reports/cv_t5_y2x.json (folds definition)
  - data/proc/model/train_dataset.parquet (features+labels)
  - data/proc/dataset/tdnet_panel.parquet (to attach eff_date)
  - data/proc/prices/jp_prices_std.parquet (for returns)

Outputs:
  - reports/checks/tdnet_model_y_2x.json (summary + per-fold + importance)
  - reports/checks/tdnet_model_y_2x_oof.parquet (ticker,date,eff_date,y,p_raw,fold)
  - reports/model_lightgbm_v2.log
"""

from __future__ import annotations
import json, yaml, os, math, warnings
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, average_precision_score
import lightgbm as lgb


ROOT = Path('.')
DATASET = ROOT / 'data/proc/model/train_dataset.parquet'
FEATSET = ROOT / 'data/proc/features_tdnet/tdnet_event_features.parquet'
FINSET  = ROOT / 'data/proc/fin/fin_quarter_norm.parquet'
PANEL   = ROOT / 'data/proc/dataset/tdnet_panel.parquet'
PRICES  = ROOT / 'data/proc/prices/jp_prices_std.parquet'
REPORTS = ROOT / 'reports'
CHECKS  = ROOT / 'reports/checks'


def log_write(msg: str):
    REPORTS.mkdir(parents=True, exist_ok=True)
    with open(REPORTS / 'model_lightgbm_v2.log', 'a', encoding='utf-8') as f:
        f.write(msg.rstrip() + '\n')


def read_cv(cv_path: Path) -> Dict:
    j = json.loads(Path(cv_path).read_text(encoding='utf-8'))
    return j


def attach_eff_date(df: pd.DataFrame, panel: pd.DataFrame) -> pd.DataFrame:
    # take first eff_date per ticker,date from panel
    p = panel[['ticker','date','eff_date']].copy()
    p['date'] = pd.to_datetime(p['date'], errors='coerce', utc=True).dt.tz_convert('UTC').dt.tz_localize(None).dt.normalize()
    p['eff_date'] = pd.to_datetime(p['eff_date'], errors='coerce', utc=True).dt.tz_convert('UTC').dt.tz_localize(None).dt.normalize()
    p = p.dropna(subset=['ticker','date','eff_date']).drop_duplicates(['ticker','date'])
    df2 = df.copy()
    df2['date'] = pd.to_datetime(df2['date'], errors='coerce', utc=True).dt.tz_convert('UTC').dt.tz_localize(None).dt.normalize()
    out = df2.merge(p, on=['ticker','date'], how='left')
    # fallback: if eff_date missing, use date+1BD approximated by next calendar day
    miss = out['eff_date'].isna()
    if miss.any():
        out.loc[miss, 'eff_date'] = pd.to_datetime(out.loc[miss, 'date']) + pd.Timedelta(days=1)
        out['eff_date'] = pd.to_datetime(out['eff_date']).dt.normalize()
    return out


def ensure_liquidity_cols(df: pd.DataFrame, px: pd.DataFrame) -> pd.DataFrame:
    # Add addv_3m and px_close as of eff_date via backward-asof merge
    if 'addv_3m' in df.columns and 'px_close' in df.columns:
        return df
    px = px.copy()
    px['date'] = pd.to_datetime(px['date'], errors='coerce').dt.normalize()
    px['volume'] = px['volume'].fillna(0)
    px['addv'] = px['adj_close'] * px['volume']
    px = px.sort_values(['ticker','date'])
    px['addv_3m'] = px.groupby('ticker')['addv'].rolling(63, min_periods=20).mean().reset_index(level=0, drop=True)
    keep = px[['ticker','date','addv_3m','adj_close']].rename(columns={'adj_close':'px_close'})
    ev = df[['ticker','eff_date']].rename(columns={'eff_date':'date'})
    outs = []
    for tkr, g in ev.groupby('ticker', sort=True):
        gp = keep[keep['ticker']==tkr][['date','addv_3m','px_close']].sort_values('date')
        if gp.empty:
            gg = g.copy(); gg['addv_3m']=np.nan; gg['px_close']=np.nan; gg['ticker']=tkr; outs.append(gg); continue
        mg = pd.merge_asof(g.sort_values('date'), gp, on='date', direction='backward', tolerance=pd.Timedelta('10D'))
        mg['ticker']=tkr
        outs.append(mg)
    aug = pd.concat(outs, ignore_index=True)
    aug = aug.rename(columns={'date':'eff_date'})
    return df.merge(aug, on=['ticker','eff_date'], how='left')


def apply_liquidity_filter(df: pd.DataFrame) -> pd.DataFrame:
    mask = pd.Series(True, index=df.index)
    if 'addv_3m' in df.columns:
        mask &= (df['addv_3m'] >= 1e8)
    if 'px_close' in df.columns:
        mask &= (df['px_close'] >= 200.0)
    if 'spread_median' in df.columns:
        mask &= (df['spread_median'] <= 0.005)
    return df[mask].copy()


def time_split_train_valid(dates: pd.Series, frac_valid: float = 0.1) -> Tuple[pd.Series, pd.Series]:
    # Return boolean masks for train/valid preserving time order
    idx = dates.sort_values().index
    n = len(idx)
    n_valid = max(1, int(math.ceil(n * frac_valid)))
    valid_idx = set(idx[-n_valid:])
    valid_mask = dates.index.isin(valid_idx)
    train_mask = ~valid_mask
    return train_mask, valid_mask


def feature_matrix(df: pd.DataFrame, label_col: str) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
    id_cols = ['ticker','date','eff_date']
    label_cols = ['y_2x','y_10x','ttd_2x','ttd_10x','dd_min_252','rel_1M','rel_3M','rel_12M',
                  'hit_rel_1M_10p','hit_rel_3M_20p','hit_rel_12M_50p']
    cols_exclude = set(id_cols + label_cols)
    keep = [c for c in df.columns if c not in cols_exclude]
    # keep only numeric features
    feat = df[keep].select_dtypes(include=[np.number])
    feat_cols = list(feat.columns)
    y = df[label_col].astype(int)
    return feat, y, feat_cols


def ret5_from_prices(px: pd.DataFrame, tickers: List[str], eff_dates: pd.Series) -> pd.Series:
    # compute 5-session forward return from eff_date
    px = px.copy()
    px['date'] = pd.to_datetime(px['date'], errors='coerce').dt.normalize()
    out = []
    for tkr, g in pd.DataFrame({'ticker':tickers, 'eff_date':eff_dates}).groupby('ticker', sort=True):
        gp = px[px['ticker']==tkr][['date','adj_close']].sort_values('date').reset_index(drop=True)
        if gp.empty:
            out.extend([np.nan]*len(g)); continue
        dates = gp['date']
        s = gp['adj_close'].values
        # map each eff_date to index then compute forward index +5
        for d in g['eff_date']:
            pos = dates.searchsorted(pd.Timestamp(d), side='left')
            if pos >= len(dates):
                out.append(np.nan); continue
            p0 = float(s[pos])
            pos2 = pos + 5
            if pos2 >= len(s):
                out.append(np.nan); continue
            p1 = float(s[pos2])
            out.append((p1 / p0) - 1.0)
    return pd.Series(out, index=eff_dates.index)


def sharpe_annualized(ret5: pd.Series, cost_bps: float = 0.0) -> Tuple[float, float]:
    if ret5 is None or ret5.empty:
        return 0.0, 0.0
    r = ret5.dropna().values
    if cost_bps:
        r = r - (float(cost_bps)/10000.0)
    mu = float(np.mean(r))
    sd = float(np.std(r, ddof=1)) if len(r) > 1 else 0.0
    sharpe = 0.0 if sd == 0.0 else mu / sd * math.sqrt(252/5)
    sharpe_net = sharpe
    return float(sharpe), float(sharpe_net)


def dsr_from_returns(ret5: pd.Series, cost_bps: float = 0.0) -> float:
    # Approximate Deflated Sharpe Ratio (Bailey & Lopez de Prado)
    if ret5 is None or ret5.dropna().shape[0] < 3:
        return 0.0
    r = ret5.dropna().values
    if cost_bps:
        r = r - (float(cost_bps)/10000.0)
    mu = float(np.mean(r)); sd = float(np.std(r, ddof=1))
    if sd == 0.0:
        return 0.0
    sr = mu / sd * math.sqrt(252/5)
    n = len(r)
    # sample skewness & excess kurtosis
    s = float(pd.Series(r).skew())
    k = float(pd.Series(r).kurt())  # excess kurtosis
    denom = math.sqrt(max(1e-12, 1 - s*sr + 0.25*(k-1)*(sr**2)))
    z = sr * math.sqrt(max(1, n - 1)) / denom
    # convert to probability via standard normal CDF
    try:
        from math import erf
        cdf = 0.5 * (1 + erf(z / math.sqrt(2)))
    except Exception:
        cdf = 0.0
    return float(cdf)


def compute_p_at_k_daily(df_scored: pd.DataFrame, k: int, label_col: str = 'y_2x') -> float:
    if df_scored.empty:
        return 0.0
    vals = []
    for d, g in df_scored.groupby('eff_date'):
        g = g.sort_values('p_raw', ascending=False).head(k)
        if g.empty: continue
        vals.append(float((g[label_col] > 0).mean()))
    return float(np.mean(vals)) if vals else 0.0


def add_fin_ratios(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    # Ensure float types
    for c in [c for c in d.columns if c.startswith('fin_')]:
        d[c] = pd.to_numeric(d[c], errors='coerce')
    # Pre-existing ratios may be present; recompute robustly where possible
    if 'fin_equity' in d.columns and 'fin_assets' in d.columns:
        d['fin_self_cap'] = d['fin_equity'] / d['fin_assets']
    if 'fin_net_profit' in d.columns and 'fin_assets' in d.columns:
        d['fin_roa'] = d['fin_net_profit'] / d['fin_assets']
    if 'fin_net_profit' in d.columns and 'fin_equity' in d.columns:
        d['fin_roe'] = d['fin_net_profit'] / d['fin_equity']
    if 'fin_op_profit' in d.columns and 'fin_sales' in d.columns:
        d['fin_opm'] = d['fin_op_profit'] / d['fin_sales']
    if 'fin_sales' in d.columns and 'fin_assets' in d.columns:
        d['fin_sales_to_assets'] = d['fin_sales'] / d['fin_assets']
    # clip extreme ratios to reasonable bounds to stabilize trees
    for c in ['fin_self_cap','fin_roa','fin_roe','fin_opm','fin_sales_to_assets']:
        if c in d.columns:
            d[c] = d[c].clip(-5.0, 5.0)
    # log-scale features for stability
    for c in ['fin_sales','fin_assets','fin_equity','fin_op_profit','fin_net_profit']:
        if c in d.columns:
            d[f'log_{c[4:]}'] = np.log1p(d[c].clip(lower=0))
    # stabilize yoy by tanh scaling
    for c in ['fin_sales_yoy','fin_op_yoy']:
        if c in d.columns:
            d[f'{c}_t'] = np.tanh(pd.to_numeric(d[c], errors='coerce')/3.0)
    return d


def event_aggregates(feat: pd.DataFrame, windows=(3,5,10,20)) -> pd.DataFrame:
    # Compute per (ticker, eff_date) rolling aggregates over past N days (exclusive)
    f = feat[['ticker','eff_date','event_strength','novelty']].copy()
    f['eff_date'] = pd.to_datetime(f['eff_date'], errors='coerce').dt.normalize()
    f = f.dropna(subset=['ticker','eff_date'])
    out_rows = []
    for tkr, g in f.groupby('ticker', sort=False):
        g = g.sort_values('eff_date').reset_index(drop=True)
        dates = g['eff_date']
        for w in windows:
            # for each row i, look back to dates >= dates[i]-w and < dates[i]
            # use two-pointer technique for O(n)
            j = 0
            cnt = []
            ssum = []
            nmean = []
            for i, di in enumerate(dates):
                d0 = di - pd.Timedelta(days=int(w))
                while j < i and dates.iloc[j] < d0:
                    j += 1
                # slice g[j:i]
                rng = g.iloc[j:i]
                cnt.append(len(rng))
                ssum.append(float(rng['event_strength'].sum()) if not rng.empty else 0.0)
                nmean.append(float(rng['novelty'].mean()) if not rng.empty else 0.0)
            out = pd.DataFrame({
                'ticker': tkr,
                'eff_date': dates.values,
                f'ev_cnt_{w}d': cnt,
                f'ev_strength_sum_{w}d': ssum,
                f'ev_novelty_mean_{w}d': nmean,
            })
            out_rows.append(out)
    agg = pd.concat(out_rows, ignore_index=True) if out_rows else pd.DataFrame()
    return agg


def add_price_features(df: pd.DataFrame, px: pd.DataFrame) -> pd.DataFrame:
    """Join price-derived features at eff_date per ticker, using only past data.
    Features: ret_5d, ret_10d (adj_close pct_change), vol_20d (rolling std of 1d returns).
    """
    if px is None or px.empty:
        return df
    p = px.copy()
    p['date'] = pd.to_datetime(p['date'], errors='coerce').dt.normalize()
    p = p.dropna(subset=['ticker','date','adj_close']).sort_values(['ticker','date'])
    out_rows = []
    for tkr, g in p.groupby('ticker', sort=False):
        g = g[['date','adj_close']].sort_values('date').reset_index(drop=True)
        r1 = g['adj_close'].pct_change(1)
        r5 = g['adj_close'].pct_change(5)
        r10= g['adj_close'].pct_change(10)
        vol20 = r1.rolling(20, min_periods=10).std()
        gg = pd.DataFrame({'ticker': tkr, 'date': g['date'].values,
                           'ret_5d': r5.values, 'ret_10d': r10.values, 'vol_20d': vol20.values})
        out_rows.append(gg)
    pf = pd.concat(out_rows, ignore_index=True) if out_rows else pd.DataFrame()
    # merge at eff_date
    m = df.merge(pf.rename(columns={'date':'eff_date'}), on=['ticker','eff_date'], how='left')
    return m


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', default='configs/tdnet_2014.yaml')
    ap.add_argument('--label', default='y_2x')
    ap.add_argument('--folds-config', default='reports/cv_t5_y2x.json')
    ap.add_argument('--cost', default='none', help='jp15bps/none')
    ap.add_argument('--class-weight', default='auto', help='auto/none')
    ap.add_argument('--use-features', action='store_true', help='use TDNET features parquet + labels instead of model/train_dataset.parquet')
    args = ap.parse_args()

    warnings.filterwarnings('ignore')
    CHECKS.mkdir(parents=True, exist_ok=True)

    # Window from config
    try:
        cfg = yaml.safe_load(Path(args.config).read_text(encoding='utf-8'))
    except Exception:
        cfg = {}
    start = str(cfg.get('params', {}).get('start_date') or '2014-01-01')
    end   = str(cfg.get('params', {}).get('end_date') or '2014-12-31')

    # Load data
    panel = pd.read_parquet(PANEL) if PANEL.exists() else pd.DataFrame()
    px = pd.read_parquet(PRICES) if PRICES.exists() else pd.DataFrame()
    if args.use_features and FEATSET.exists():
        df = pd.read_parquet(FEATSET)
        df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.normalize()
        df['eff_date'] = pd.to_datetime(df.get('eff_date'), errors='coerce').dt.normalize()
        # join finance as-of
        if FINSET.exists():
            fin = pd.read_parquet(FINSET).copy()
            fin['period_end'] = pd.to_datetime(fin['period_end'], errors='coerce').dt.normalize()
            fin['disclosed_date'] = pd.to_datetime(fin['disclosed_date'], errors='coerce').dt.normalize()
            fin['asof_date'] = fin['disclosed_date']
            fin.loc[fin['asof_date'].isna(), 'asof_date'] = fin['period_end']
            fin = fin[fin['q_flag'].astype(str).str.contains('Q', na=False)]
            fin_cols = ['sales','op_profit','ord_profit','net_profit','assets','equity','eps','opm','roe','roa','self_cap','sales_yoy','op_yoy']
            parts = []
            for t, g in df.groupby('ticker', sort=False):
                gf = fin[fin['ticker']==t]
                if gf.empty: continue
                m = pd.merge_asof(g.sort_values('eff_date'), gf[['asof_date']+fin_cols].sort_values('asof_date'), left_on='eff_date', right_on='asof_date', direction='backward')
                parts.append(m)
            df = pd.concat(parts, ignore_index=True) if parts else df
            add_map = {c: f'fin_{c}' for c in fin_cols}
            df = df.rename(columns=add_map)
        # liquidity cols from prices
        df = ensure_liquidity_cols(df, px) if not px.empty else df
        df = apply_liquidity_filter(df)
        # price-derived features (as-of eff_date)
        try:
            df = add_price_features(df, px)
        except Exception:
            pass
        # add derived finance ratios and event aggregates
        try:
            df = add_fin_ratios(df)
        except Exception:
            pass
        try:
            feat_src = pd.read_parquet(FEATSET)
            agg = event_aggregates(feat_src, windows=(3,5,10,20))
            df = df.merge(agg, on=['ticker','eff_date'], how='left')
        except Exception:
            pass
        # attach labels
        lab_path = ROOT / 'data/proc/labels/targets.parquet'
        if lab_path.exists():
            y = pd.read_parquet(lab_path)[['ticker','date',args.label]].copy()
            y['date'] = pd.to_datetime(y['date'], errors='coerce').dt.normalize()
            df = df.merge(y, on=['ticker','date'], how='left')
            df = df.dropna(subset=[args.label]).copy()
        else:
            df[args.label] = pd.NA
    else:
        df = pd.read_parquet(DATASET)
        df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.normalize()
        # Attach eff_date and liquidity
        df = attach_eff_date(df, panel)
        df = ensure_liquidity_cols(df, px) if not px.empty else df
        df = apply_liquidity_filter(df)

    # restrict to window on eff_date
    e = pd.Timestamp(end)
    if args.use_features:
        # allow training from earlier history; cap only by end
        df = df[(df['eff_date']<=e)].copy()
    else:
        s = pd.Timestamp(start)
        df = df[(df['eff_date']>=s) & (df['eff_date']<=e)].copy()

    # Folds
    cv = read_cv(Path(args.folds_config))
    purge_days = int(cv.get('purge_days', 20))
    embargo_days = int(cv.get('embargo_days', 5))
    folds = [(pd.Timestamp(f['test_start']), pd.Timestamp(f['test_end'])) for f in cv['folds']]

    X_all, y_all, feat_cols = feature_matrix(df, args.label)
    dates_eff = df['eff_date']
    tickers = df['ticker']
    dates_evt = df['date']

    # LightGBM base params
    base_params = dict(
        objective='binary',
        max_depth=-1,
        learning_rate=0.05,
        n_estimators=1500,
        n_jobs=-1,
        random_state=42,
    )
    class_weight = 'balanced' if (args.class_weight or '').lower() in ('auto','balanced','true','yes') else None

    oof = pd.DataFrame({'ticker': tickers, 'date': dates_evt, 'eff_date': dates_eff, 'y': y_all.values, 'p_raw': np.nan, 'fold': np.nan})
    fold_metrics = []
    feat_gain = np.zeros(len(feat_cols), dtype=float)

    for i,(tstart,tend) in enumerate(folds, start=1):
        va_mask = (dates_eff>=tstart) & (dates_eff<=tend)
        n_va = int(va_mask.sum())
        if n_va == 0:
            fold_metrics.append({'fold': i, 'n_train': 0, 'n_test': 0, 'skipped': True, 'reason': 'no_validation_rows'})
            continue
        # walk-forward: train strictly before test window with purge
        cutoff = tstart - pd.Timedelta(days=purge_days)
        tr_mask = (dates_eff < cutoff)
        n_tr = int(tr_mask.sum())
        if n_tr == 0:
            fold_metrics.append({'fold': i, 'n_train': 0, 'n_test': n_va, 'skipped': True, 'reason': 'no_training_rows'})
            continue

        X_tr = X_all.loc[tr_mask]
        y_tr = y_all.loc[tr_mask]
        X_va = X_all.loc[va_mask]
        y_va = y_all.loc[va_mask]

        # time-based validation split from training for early stopping
        tr_submask, va_submask = time_split_train_valid(dates_eff[tr_mask], frac_valid=0.1)
        X_tr2, y_tr2 = X_tr.loc[tr_submask], y_tr.loc[tr_submask]
        X_es, y_es   = X_tr.loc[va_submask], y_tr.loc[va_submask]
        # Skip if single-class in train or valid
        if len(np.unique(y_tr2)) < 2 or len(np.unique(y_es)) < 2 or len(np.unique(y_va)) < 2:
            fold_metrics.append({'fold': i, 'n_train': n_tr, 'n_test': n_va, 'skipped': True, 'reason': 'single_class'})
            continue
        # grid search (small but richer)
        grid = []
        for nl in [31,63,127]:
            for mcs in [20,50,100]:
                for ss in [0.7,0.8,0.9]:
                    for cs in [0.6,0.8]:
                        grid.append(dict(num_leaves=nl, min_child_samples=mcs, subsample=ss, colsample_bytree=cs))
        pos = float((y_tr2==1).sum()); neg = float((y_tr2==0).sum())
        scale_pos_weight = None
        if pos > 0 and neg > 0:
            scale_pos_weight = max(1.0, neg/pos)

        best_auc_es = -1.0
        best_model = None
        best_used_params = None
        for hp in grid:
            p = base_params.copy(); p.update(hp)
            if class_weight is None and scale_pos_weight is not None:
                p['scale_pos_weight'] = scale_pos_weight
            model = lgb.LGBMClassifier(**p, class_weight=class_weight)
            model.fit(
                X_tr2, y_tr2,
                eval_set=[(X_es, y_es)],
                eval_metric='auc',
                callbacks=[lgb.early_stopping(stopping_rounds=200, verbose=False)]
            )
            pred_es = model.predict_proba(X_es)[:,1]
            try:
                auc_es = roc_auc_score(y_es, pred_es)
            except Exception:
                auc_es = float('nan')
            if np.isfinite(auc_es) and auc_es > best_auc_es:
                best_auc_es = float(auc_es)
                best_model = model
                best_used_params = p

        if best_model is None:
            fold_metrics.append({'fold': i, 'n_train': n_tr, 'n_test': n_va, 'skipped': True, 'reason': 'no_model'})
            continue
        pred = best_model.predict_proba(X_va)[:,1]
        oof.loc[va_mask, 'p_raw'] = pred
        oof.loc[va_mask, 'fold'] = i

        # feature importance (gain)
        try:
            feat_gain += best_model.booster_.feature_importance(importance_type='gain')
        except Exception:
            pass

        auc = roc_auc_score(y_va, pred) if len(np.unique(y_va))>1 else float('nan')
        apr = average_precision_score(y_va, pred) if len(y_va)>0 else float('nan')
        fold_metrics.append({'fold': i, 'n_train': n_tr, 'n_test': n_va, 'auc_roc': float(auc), 'auc_pr': float(apr), 'params': {k: best_used_params.get(k) for k in ['num_leaves','min_child_samples','subsample','colsample_bytree','scale_pos_weight']}})

    # Save OOF
    oof_path = CHECKS / 'tdnet_model_y_2x_oof.parquet'
    oof.to_parquet(oof_path, index=False)

    # Global metrics
    oof_valid = oof.dropna(subset=['p_raw'])
    auc_oof = roc_auc_score(oof_valid['y'], oof_valid['p_raw']) if not oof_valid.empty and len(np.unique(oof_valid['y']))>1 else None
    apr_oof = average_precision_score(oof_valid['y'], oof_valid['p_raw']) if not oof_valid.empty else None

    # P@K based on eff_date
    p100 = compute_p_at_k_daily(oof_valid[['eff_date','y']].assign(p_raw=oof_valid['p_raw']), k=100, label_col='y')
    p200 = compute_p_at_k_daily(oof_valid[['eff_date','y']].assign(p_raw=oof_valid['p_raw']), k=200, label_col='y')

    # Build portfolio 5D returns from prices for scored universe @ eff_date
    # Use top-100 each eff_date
    port_rets = []
    for d, g in oof_valid.groupby('eff_date'):
        gg = g.sort_values('p_raw', ascending=False).head(100)
        if gg.empty:
            continue
        r5 = ret5_from_prices(px, gg['ticker'].tolist(), gg['eff_date'])
        port_rets.append(pd.Series([float(r5.mean())], index=[pd.Timestamp(d)]))
    ret5_series = (pd.concat(port_rets) if port_rets else pd.Series(dtype=float)).sort_index()

    cost_bps = 15.0 if (args.cost or '').lower().startswith('jp15') else 0.0
    sh, sh_net = sharpe_annualized(ret5_series, cost_bps=cost_bps)
    dsr = dsr_from_returns(ret5_series, cost_bps=cost_bps)

    # Feature importance summary
    fi = pd.DataFrame({'feature': feat_cols, 'gain': feat_gain})
    fi = fi.sort_values('gain', ascending=False)
    fi_top = fi.head(50).to_dict(orient='records')

    # pick best fold params if available
    best_params_global = None
    try:
        fm = pd.DataFrame(fold_metrics)
        fm_ok = fm[fm['auc_roc'].apply(lambda x: isinstance(x, (float,int)) and np.isfinite(x))]
        if not fm_ok.empty and 'params' in fm_ok.columns:
            idxmax = int(fm_ok['auc_roc'].astype(float).idxmax())
            best_params_global = fold_metrics[idxmax].get('params')
    except Exception:
        pass

    summ = {
        'label': args.label,
        'rows': int(len(df)),
        'folds': len(fold_metrics),
        'oof': {
            'auc_roc': None if auc_oof is None else float(auc_oof),
            'auc_pr': None if apr_oof is None else float(apr_oof),
            'p_at_k_100': float(p100),
            'p_at_k_200': float(p200),
            'sharpe_annualized': float(sh),
            'sharpe_annualized_net': float(sh_net),
            'dsr': float(dsr),
        },
        'fold_metrics': fold_metrics,
        'feature_importance_top': fi_top,
        'best_params': best_params_global,
    }
    (CHECKS / 'tdnet_model_y_2x.json').write_text(json.dumps(summ, ensure_ascii=False, indent=2), encoding='utf-8')
    log_write(json.dumps({'oof_rows': int(len(oof_valid)), 'auc_roc': summ['oof']['auc_roc'], 'p@k100': p100}, ensure_ascii=False))
    print(json.dumps({'oof_rows': int(len(oof_valid)), 'auc_roc': summ['oof']['auc_roc'], 'p@k100': p100}, ensure_ascii=False))


if __name__ == '__main__':
    main()
