#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bulk backfill JP prices from J-Quants (premium), resume-safe.

Inputs:
  - Env: JQ_EMAIL, JQ_PASSWORD
  - Universe: tickers from features_tdnet since 2013-09-01 (code4 extracted)

Fetch:
  - GET /v1/prices/daily_quotes?code=####&from=F&to=T
  - Window default: 2000-01-01 .. today
  - Handles 401 -> refresh; backoff on 5xx

Outputs:
  - data/raw/jquants/prices/####.parquet
    columns: ticker,date,adj_close,volume,source='jquants'

Idempotent: skips symbols already saved.
"""

from __future__ import annotations
import os, sys, json, time, re
from pathlib import Path
from datetime import date as _date
import pandas as pd
import requests as rq


ROOT = Path('.')
FEAT = ROOT / 'data/proc/features_tdnet/tdnet_event_features.parquet'
OUTDIR = ROOT / 'data/raw/jquants/prices'; OUTDIR.mkdir(parents=True, exist_ok=True)
TOK = ROOT / '.secrets/jq_tokens.json'; TOK.parent.mkdir(parents=True, exist_ok=True)

EMAIL = os.environ.get('JQ_EMAIL'); PASS = os.environ.get('JQ_PASSWORD')
AUTH_USER    = "https://api.jquants.com/v1/token/auth_user"
AUTH_REFRESH = "https://api.jquants.com/v1/token/auth_refresh"
DAILY_QUOTES = "https://api.jquants.com/v1/prices/daily_quotes"

FROM_DEFAULT = '2000-01-01'
TO_DEFAULT   = _date.today().isoformat()


def _save_tokens(d): TOK.write_text(json.dumps(d), encoding='utf-8')
def _load_tokens():
    if TOK.exists():
        try: return json.loads(TOK.read_text(encoding='utf-8'))
        except: return {}
    return {}

def _get_idtoken(log: bool = False) -> str | None:
    t=_load_tokens()
    if t.get('refreshToken'):
        try:
            r=rq.post(AUTH_REFRESH, params={'refreshtoken': t['refreshToken']}, timeout=15)
            if r.ok and r.json().get('idToken'):
                t['idToken']=r.json()['idToken']; _save_tokens(t); return t['idToken']
        except Exception as e:
            if log: print(f'[jq] auth_refresh error: {e}')
    if not (EMAIL and PASS):
        return None
    r=rq.post(AUTH_USER, json={'mailaddress': EMAIL, 'password': PASS}, timeout=15)
    if not r.ok:
        return None
    rt=(r.json() or {}).get('refreshToken')
    if not rt:
        return None
    t={'refreshToken': rt}
    r2=rq.post(AUTH_REFRESH, params={'refreshtoken': rt}, timeout=15)
    if not r2.ok:
        return None
    it=(r2.json() or {}).get('idToken')
    if not it:
        return None
    t['idToken']=it; _save_tokens(t); return it


def jq_fetch_daily(code4: str, start: str, end: str, tries=4):
    it=_get_idtoken(log=True)
    if not it:
        return None
    for k in range(tries):
        try:
            r=rq.get(DAILY_QUOTES, params={'code': code4, 'from': start, 'to': end}, headers={'Authorization': f'Bearer {it}'}, timeout=30)
        except Exception:
            time.sleep(1.0*(k+1)); continue
        if r.status_code==401:
            it=_get_idtoken(log=True); time.sleep(0.5); continue
        if not r.ok:
            time.sleep(1.0*(k+1)); continue
        try:
            j=r.json() or {}
        except Exception:
            return None
        rows=j.get('daily_quotes') or j.get('data') or []
        if not rows: return None
        df=pd.DataFrame(rows)
        if not {'Date','Close'}.issubset(df.columns):
            return None
        out=pd.DataFrame({
            'ticker': f'{code4}.T',
            'date':   pd.to_datetime(df['Date']).dt.normalize(),
            'adj_close': pd.to_numeric(df['Close'], errors='coerce'),
            'volume':    pd.to_numeric(df.get('Volume'), errors='coerce'),
            'source': 'jquants',
        }).dropna(subset=['date','adj_close'])
        return out if not out.empty else None
    return None


def load_universe() -> list[str]:
    if not FEAT.exists():
        return []
    d=pd.read_parquet(FEAT, columns=['ticker','date'])
    d['date']=pd.to_datetime(d['date'], errors='coerce')
    d=d.dropna(subset=['date'])
    d=d[d['date']>='2013-09-01']
    codes=set()
    for t in d['ticker'].astype(str).str.upper().tolist():
        m=re.fullmatch(r'(\d{4})\.T', t)
        if m: codes.add(m.group(1))
    return sorted(codes)


def main():
    codes=load_universe()
    if not codes:
        print(json.dumps({'prices_ok':0,'prices_fail':0,'note':'no_universe'}, ensure_ascii=False)); return
    ok=fail=0; samples=[]
    for i, c4 in enumerate(codes, 1):
        outp=OUTDIR/f'{c4}.parquet'
        if outp.exists():
            ok+=1; continue
        df=jq_fetch_daily(c4, FROM_DEFAULT, TO_DEFAULT)
        if df is None or df.empty:
            fail+=1
        else:
            df.to_parquet(outp, index=False); ok+=1
            if len(samples)<5:
                samples.append({'code': c4, 'rows': int(len(df))})
        if i%50==0:
            time.sleep(0.5)
    print(json.dumps({'prices_ok': ok, 'prices_fail': fail, 'universe': len(codes), 'out_dir': str(OUTDIR), 'samples': samples}, ensure_ascii=False))


if __name__=='__main__':
    main()

