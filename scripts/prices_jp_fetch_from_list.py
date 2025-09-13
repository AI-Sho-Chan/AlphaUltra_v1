#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fetch JP prices for a list of tickers with multi-source fallback.

Order: stooq -> yfinance -> j-quants -> eodhd (first that returns Date/Close)

Input:
  - CSV list file (one ticker per line, e.g., 7203.T)

Output per symbol (saved under data/raw/prices):
  - stooq_<code4>.parquet, yf_<code4>.parquet, jq_<code4>.parquet, eod_<code4>.parquet
    Columns: ticker,date,adj_close,volume

Extras:
  - J-Quants token flow logging (auth_user / auth_refresh)
  - Print first 300 chars of JSON for one code (prefer 7203) to diagnose payload shape
  - Expands date window to 2000-01-01..2025-12-31

Env vars (optional):
  - JQ_EMAIL, JQ_PASSWORD  (for J-Quants)
  - EOD_API_TOKEN          (for eodhistoricaldata.com)
"""

from __future__ import annotations
import os, sys, io, json, time, re, argparse, logging
from pathlib import Path
from typing import Optional

import pandas as pd
import requests as rq

try:
    import yfinance as yf  # type: ignore
except Exception:  # yfinance optional; skip if missing
    yf = None  # type: ignore

ROOT = Path('.')
RAW = ROOT / 'data/raw/prices'
RAW.mkdir(parents=True, exist_ok=True)

DEFAULT_FROM = '2000-01-01'
DEFAULT_TO   = '2025-12-31'

# --- Helpers
UA = {"User-Agent": "alphaai-price-fetcher/1.0"}

def _norm_df(ticker: str, df: pd.DataFrame, date_col: str, close_col: str, vol_col: Optional[str] = None) -> Optional[pd.DataFrame]:
    if df is None or df.empty:
        return None
    if date_col not in df.columns or close_col not in df.columns:
        return None
    out = pd.DataFrame({
        'ticker': ticker,
        'date': pd.to_datetime(df[date_col], errors='coerce').dt.normalize(),
        'adj_close': pd.to_numeric(df[close_col], errors='coerce'),
        'volume': pd.to_numeric(df.get(vol_col) if vol_col else None, errors='coerce') if vol_col else None,
    })
    out = out.dropna(subset=['date', 'adj_close']).reset_index(drop=True)
    return out if not out.empty else None

def _code4(ticker: str) -> Optional[str]:
    m = re.fullmatch(r"(\d{4})\.T", ticker.strip().upper())
    return m.group(1) if m else None

# --- Source: Stooq CSV
def fetch_stooq_csv(ticker: str) -> Optional[pd.DataFrame]:
    code = _code4(ticker)
    if not code:
        return None
    url = f"https://stooq.com/q/d/l/?s={code.lower()}.jp&i=d"
    try:
        r = rq.get(url, timeout=20, headers=UA)
        if r.status_code != 200:
            return None
        df = pd.read_csv(io.StringIO(r.text))
    except Exception:
        return None
    return _norm_df(ticker, df, 'Date', 'Close', 'Volume')

# --- Source: Yahoo Finance
def fetch_yfinance(ticker: str, start: str, end: str) -> Optional[pd.DataFrame]:
    if yf is None:
        return None
    try:
        logging.getLogger('yfinance').setLevel(logging.ERROR)
        t = yf.Ticker(ticker)
        d = t.history(start=start, end=end, auto_adjust=True)
    except Exception:
        return None
    if d is None or d.empty:
        return None
    d = d.reset_index()
    return _norm_df(ticker, d, 'Date', 'Close', 'Volume')

# --- Source: J-Quants REST
JQ_AUTH_USER    = "https://api.jquants.com/v1/token/auth_user"
JQ_AUTH_REFRESH = "https://api.jquants.com/v1/token/auth_refresh"
JQ_DAILY_QUOTES = "https://api.jquants.com/v1/prices/daily_quotes"

JQ_EMAIL = os.environ.get('JQ_EMAIL')
JQ_PASSWORD = os.environ.get('JQ_PASSWORD')
JQ_TOK_PATH = ROOT / '.secrets/jq_tokens.json'
JQ_TOK_PATH.parent.mkdir(parents=True, exist_ok=True)

def _jq_load_tokens() -> dict:
    if JQ_TOK_PATH.exists():
        try:
            return json.loads(JQ_TOK_PATH.read_text(encoding='utf-8'))
        except Exception:
            return {}
    return {}

def _jq_save_tokens(d: dict) -> None:
    try:
        JQ_TOK_PATH.write_text(json.dumps(d), encoding='utf-8')
    except Exception:
        pass

def _jq_get_idtoken(log: bool = False) -> Optional[str]:
    if not (JQ_EMAIL and JQ_PASSWORD):
        return None
    t = _jq_load_tokens()
    # Try refresh first
    if t.get('refreshToken'):
        try:
            if log: print('[jquants] auth_refresh using existing refreshToken...')
            r = rq.post(JQ_AUTH_REFRESH, params={'refreshtoken': t['refreshToken']}, timeout=15)
            if r.ok and r.json().get('idToken'):
                t['idToken'] = r.json()['idToken']
                _jq_save_tokens(t)
                if log: print('[jquants] auth_refresh ok -> idToken')
                return t['idToken']
        except Exception as e:
            if log: print(f'[jquants] auth_refresh error: {e}')
    # Fresh login
    try:
        if log: print('[jquants] auth_user with email/password...')
        r = rq.post(JQ_AUTH_USER, json={'mailaddress': JQ_EMAIL, 'password': JQ_PASSWORD}, timeout=15)
        r.raise_for_status()
        rt = (r.json() or {}).get('refreshToken')
        if log: print(f"[jquants] auth_user refreshToken present={bool(rt)}")
        if not rt:
            return None
        t = {'refreshToken': rt}
        r2 = rq.post(JQ_AUTH_REFRESH, params={'refreshtoken': rt}, timeout=15)
        r2.raise_for_status()
        it = (r2.json() or {}).get('idToken')
        if log: print(f"[jquants] auth_refresh idToken present={bool(it)}")
        if not it:
            return None
        t['idToken'] = it
        _jq_save_tokens(t)
        return it
    except Exception as e:
        if log: print(f'[jquants] auth flow error: {e}')
        return None

_jq_logged_sample = False

def fetch_jquants(ticker: str, start: str, end: str) -> Optional[pd.DataFrame]:
    code = _code4(ticker)
    if not code:
        return None
    it = _jq_get_idtoken(log=True)
    if not it:
        return None
    global _jq_logged_sample
    for k in range(3):
        try:
            r = rq.get(
                JQ_DAILY_QUOTES,
                params={'code': code, 'from': start, 'to': end},
                headers={'Authorization': f'Bearer {it}'},
                timeout=30,
            )
        except Exception:
            time.sleep(1.0 * (k + 1))
            continue
        if r.status_code == 401:
            # refresh and retry
            if not (it := _jq_get_idtoken(log=True)):
                return None
            time.sleep(0.5)
            continue
        if not r.ok:
            time.sleep(1.0 * (k + 1))
            continue
        try:
            j = r.json() or {}
        except Exception:
            return None
        # Log first ~300 chars for one code (prefer 7203)
        if not _jq_logged_sample and (code == '7203' or True):
            s = json.dumps(j)[:300]
            print(f"[jquants] sample json for {code}: {s}...")
            _jq_logged_sample = True
        rows = j.get('daily_quotes') or j.get('data') or []
        if not rows:
            return None
        df = pd.DataFrame(rows)
        # J-Quants fields are typically Date, Open, High, Low, Close, Volume
        return _norm_df(ticker, df, 'Date', 'Close', 'Volume')
    return None

# --- Source: EOD Historical Data (optional)
EOD_TOKEN = os.environ.get('EOD_API_TOKEN')

def fetch_eodhd(ticker: str, start: str, end: str) -> Optional[pd.DataFrame]:
    if not EOD_TOKEN:
        return None
    # EODHD Tokyo uses .TSE (not .T)
    sym = ticker
    if ticker.upper().endswith('.T'):
        sym = ticker[:-2] + '.TSE'
    url = f"https://eodhistoricaldata.com/api/eod/{sym}"
    try:
        r = rq.get(url, params={'from': start, 'to': end, 'fmt': 'json', 'adjusted': 1, 'api_token': EOD_TOKEN, 'period': 'd', 'order': 'a'}, timeout=25)
        if not r.ok:
            return None
        arr = r.json() or []
        if not isinstance(arr, list) or not arr:
            return None
        df = pd.DataFrame(arr)
    except Exception:
        return None
    # EODHD fields: date, close, volume
    # Sometimes uppercase/lowercase differ; normalize
    cols = {c.lower(): c for c in df.columns}
    dcol = cols.get('date')
    ccol = cols.get('close')
    vcol = cols.get('volume')
    if not (dcol and ccol):
        return None
    return _norm_df(ticker, df, dcol, ccol, vcol)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('list', nargs='?', default=str(ROOT / 'data/tmp/tickers_20141114.csv'))
    ap.add_argument('--start', default=DEFAULT_FROM)
    ap.add_argument('--end', default=DEFAULT_TO)
    args = ap.parse_args()

    LIST = Path(args.list)
    FROM = args.start
    TO = args.end

    if not LIST.exists():
        print(f"[prices_from_list] list not found: {LIST}")
        sys.exit(2)

    tickers = [l.strip().upper() for l in LIST.read_text(encoding='utf-8').splitlines() if l.strip()]
    # De-dup and keep only ####.T
    todo = []
    for t in tickers:
        if _code4(t):
            todo.append(t)

    # cache existing by any source
    have = set([p.name.split('_', 1)[-1].split('.')[0] for p in RAW.glob('*.parquet')])
    # compare with code4
    todo = [t for t in todo if _code4(t).lower() not in have]

    ok = fail = 0
    for i, t in enumerate(todo, 1):
        code = _code4(t)
        if not code:
            continue
        # Try sources in order
        df = fetch_stooq_csv(t)
        if df is not None:
            df.to_parquet(RAW / f'stoo q_{code.lower()}.parquet'.replace(' ', ''), index=False)
            ok += 1
            pass
        else:
            df = fetch_yfinance(t, FROM, TO)
            if df is not None:
                df.to_parquet(RAW / f'yf_{code.lower()}.parquet', index=False)
                ok += 1
            else:
                df = fetch_jquants(t, FROM, TO)
                if df is not None:
                    df.to_parquet(RAW / f'jq_{code.lower()}.parquet', index=False)
                    ok += 1
                else:
                    df = fetch_eodhd(t, FROM, TO)
                    if df is not None:
                        df.to_parquet(RAW / f'eod_{code.lower()}.parquet', index=False)
                        ok += 1
                    else:
                        fail += 1

        # light pacing in case of rate limits
        if i % 50 == 0:
            time.sleep(0.5)

    print({
        'list': str(LIST),
        'todo': len(todo),
        'ok': ok,
        'fail': fail,
        'from': FROM,
        'to': TO,
        'jq_enabled': bool(JQ_EMAIL and JQ_PASSWORD),
        'eod_enabled': bool(EOD_TOKEN),
    })


if __name__ == '__main__':
    main()
