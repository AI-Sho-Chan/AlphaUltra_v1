#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bulk fetch quarterly financials from J-Quants (premium), resume-safe.

Official endpoints (quarterly):
  - /v1/statements?code=####&from=YYYY-MM-DD&to=YYYY-MM-DD&type=Q
  - fallback: /v1/statements/quarters?code=####&from=...&to=...
  - optional: /v1/statements/indicator?code=####&from=...&to=...&type=Q

Output per code:
  data/raw/jquants/fin/####.parquet, minimal schema:
    [code, ticker, period_end, q_flag, fs_type, metrics(json), source='jquants']
"""

from __future__ import annotations
import os, sys, json, time, re, random
from pathlib import Path
from datetime import date as _date
import argparse
import pandas as pd
import requests as rq

ROOT = Path('.')
FEAT = ROOT / 'data/proc/features_tdnet/tdnet_event_features.parquet'
OUTDIR = ROOT / 'data/raw/jquants/fin'; OUTDIR.mkdir(parents=True, exist_ok=True)
# support both token file names for backward compatibility
TOK_NEW = ROOT / '.secrets/jq_token.json'
TOK_OLD = ROOT / '.secrets/jq_tokens.json'
ENV = ROOT / '.secrets/jq.env'
CUR = ROOT / '.secrets/backfill_cursor.json'

def _load_env_from_file():
    if ENV.exists():
        try:
            for line in ENV.read_text(encoding='utf-8').splitlines():
                # strip whitespace and potential BOM
                line=line.lstrip('\ufeff').strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k,v=line.split('=',1)
                k=k.lstrip('\ufeff').strip(); v=v.strip()
                if k in ('JQ_EMAIL','JQ_PASSWORD') and v:
                    os.environ[k]=v
        except Exception:
            pass

_load_env_from_file()
EMAIL=os.environ.get('JQ_EMAIL'); PASS=os.environ.get('JQ_PASSWORD')
AUTH_USER    = "https://api.jquants.com/v1/token/auth_user"
AUTH_REFRESH = "https://api.jquants.com/v1/token/auth_refresh"

FROM_DEFAULT='2000-01-01'
TO_DEFAULT=_date.today().isoformat()


def _save_tokens(d: dict):
    try:
        TOK_NEW.parent.mkdir(parents=True, exist_ok=True)
        TOK_NEW.write_text(json.dumps(d), encoding='utf-8')
        # also write legacy path
        TOK_OLD.write_text(json.dumps(d), encoding='utf-8')
    except Exception:
        pass

def _load_tokens() -> dict:
    for p in (TOK_NEW, TOK_OLD):
        if p.exists():
            try:
                return json.loads(p.read_text(encoding='utf-8'))
            except Exception:
                return {}
    return {}

def _get_idtoken(log: bool=False, verbose: bool=False) -> str|None:
    """
    Load tokens from .secrets/jq_token.json (or legacy jq_tokens.json) and try refresh.
    If refreshToken missing or refresh fails, fall back to auth_user using JQ_EMAIL/JQ_PASSWORD.
    Persist refreshed tokens.
    """
    # try refresh using existing token file
    t=_load_tokens() or {}
    rt=t.get('refreshToken')
    if rt:
        try:
            r=rq.post(AUTH_REFRESH, params={'refreshtoken': rt}, timeout=15)
            if verbose:
                print(f"[jq-auth] refresh -> {r.status_code}")
            if r.ok:
                it=(r.json() or {}).get('idToken')
                if it:
                    t['idToken']=it; _save_tokens(t); return it
        except Exception as e:
            if log: print(f'[jq-fin] auth_refresh error: {e}')
    # fallback to auth_user if creds present
    if EMAIL and PASS:
        # try auth_user with limited retries respecting Retry-After
        for k in range(5):
            try:
                r=rq.post(AUTH_USER, json={'mailaddress': EMAIL, 'password': PASS}, timeout=20)
                if verbose:
                    print(f"[jq-auth] auth_user -> {r.status_code}")
                if r.status_code==429:
                    ra=r.headers.get('Retry-After')
                    if ra:
                        try: time.sleep(min(30.0, float(ra)))
                        except: _sleep_backoff(k)
                    else:
                        _sleep_backoff(k)
                    continue
                if not r.ok:
                    _sleep_backoff(k)
                    continue
                rt=(r.json() or {}).get('refreshToken')
                if not rt:
                    _sleep_backoff(k)
                    continue
                t={'refreshToken': rt}
                r2=rq.post(AUTH_REFRESH, params={'refreshtoken': rt}, timeout=15)
                if verbose:
                    print(f"[jq-auth] auth_refresh(after user) -> {r2.status_code}")
                if not r2.ok:
                    _sleep_backoff(k)
                    continue
                it=(r2.json() or {}).get('idToken')
                if it:
                    t['idToken']=it; _save_tokens(t); return it
            except Exception as e:
                if log: print(f'[jq-fin] auth_user error: {e}')
                _sleep_backoff(k)
    return None


def load_universe() -> list[str]:
    codes=set()
    # from features (Phase-1 window)
    if FEAT.exists():
        d=pd.read_parquet(FEAT, columns=['ticker','date'])
        d['date']=pd.to_datetime(d['date'], errors='coerce')
        d=d.dropna(subset=['date'])
        d=d[d['date']>='2013-09-01']
        for t in d['ticker'].astype(str).str.upper().tolist():
            m=re.fullmatch(r'(\d{4})\.T', t)
            if m: codes.add(m.group(1))
    # add from local price caches (yfinance/stooq/jquants)
    for root in [Path('data/raw/prices'), Path('data/raw/jquants/prices')]:
        if not root.exists():
            continue
        for fp in root.glob('*.parquet'):
            name=fp.name.lower()
            m=re.match(r'^(?:yf|stooq|jq|jquants|eodhd|eod)_([0-9]{4})\.', name)
            if m:
                codes.add(m.group(1))
            else:
                try:
                    d=pd.read_parquet(fp, columns=['ticker'])
                    for t in d['ticker'].astype(str).str.upper().tolist():
                        m=re.fullmatch(r'(\d{4})\.T', t)
                        if m: codes.add(m.group(1))
                except Exception:
                    pass
    return sorted(codes)


def _infer_fs_type(rec: dict, endpoint_hint: str) -> str:
    t = (rec.get('Type') or rec.get('TypeOfStatements') or rec.get('StatementType') or '').upper()
    if t in {'BS','PL','CF','IND'}:
        return t
    if 'indicator' in endpoint_hint.lower():
        return 'IND'
    txt = json.dumps(rec).lower()
    if any(k in txt for k in ['netsales','revenue','operatingincome','profit','ordinaryincome','eps']):
        return 'PL'
    if any(k in txt for k in ['assets','liabilities','equity','netassets']):
        return 'BS'
    if any(k in txt for k in ['cashflows','cashflow','operatingactivities','financingactivities','investingactivities']):
        return 'CF'
    return 'IND'

def _quarter_flag(dt: pd.Timestamp) -> str:
    m = int(dt.month); q=(m-1)//3+1; return f'Q{q}'

def _sleep_backoff(k: int, base: float = 0.5, cap: float = 30.0):
    wait = min(cap, base * (2 ** max(0, k))) + random.uniform(0.0, 0.5)
    time.sleep(wait)


def jq_fetch_fin_q(code4: str, start: str, end: str, tries=6, stats: dict | None = None, verbose: bool=False):
    it=_get_idtoken(log=True, verbose=verbose)
    if not it:
        if stats is not None:
            stats['no_token']=stats.get('no_token',0)+1
        return None
    urls=[
        ("https://api.jquants.com/v1/fins/statements", {"type":"Q"}),
        ("https://api.jquants.com/v1/fins/statements", {}),
    ]
    for u, extra in urls:
        for k in range(tries):
            try:
                params={'code': code4, 'from': start, 'to': end}
                params.update(extra)
                r=rq.get(u, params=params, headers={'Authorization': f'Bearer {it}'}, timeout=30)
            except Exception:
                if stats is not None: stats['exc']=stats.get('exc',0)+1
                _sleep_backoff(k); continue
            sc = int(r.status_code)
            if verbose:
                print(f"[jq] {code4} GET {u} -> {sc}")
            if sc==401:
                if stats is not None: stats['401']=stats.get('401',0)+1
                it=_get_idtoken(log=True); time.sleep(0.5); continue
            if sc==429:
                if stats is not None: stats['429']=stats.get('429',0)+1
                ra = r.headers.get('Retry-After')
                if ra:
                    try:
                        time.sleep(min(30.0, float(ra)))
                    except Exception:
                        _sleep_backoff(k)
                else:
                    _sleep_backoff(k)
                continue
            if 500 <= sc < 600:
                if stats is not None: stats['5xx']=stats.get('5xx',0)+1
                _sleep_backoff(k); continue
            if sc in (403, 404):
                if stats is not None: stats[str(sc)]=stats.get(str(sc),0)+1
                return None
            if not r.ok:
                if stats is not None: stats['other']=stats.get('other',0)+1
                _sleep_backoff(k); continue
            try:
                j=r.json() or {}
            except Exception:
                return None
            rows=j.get('statements') or j.get('data') or []
            if not rows:
                # treat as soft fail -> backoff and retry
                _sleep_backoff(k); continue
            out_rows=[]
            for rec in rows:
                # period end normalization
                per=None
                for cand in ['CurrentPeriodEndDate','EndDate','DisclosedDate','Date','ResultDate','FiscalPeriodEnd','PeriodEnd']:
                    val=rec.get(cand)
                    if val:
                        per=pd.to_datetime(val, errors='coerce')
                        break
                if per is None or pd.isna(per):
                    continue
                per=per.normalize()
                qraw=(rec.get('TypeOfCurrentPeriod') or rec.get('Quarter') or '').upper()
                if 'FY' in qraw and 'Q' not in qraw:
                    continue
                qflag=qraw if qraw else _quarter_flag(per)
                # fs_type from TypeOfDocument hint if possible
                tdoc = (rec.get('TypeOfDocument') or '').upper()
                if 'CASH' in tdoc:
                    fs_type='CF'
                elif 'BALANCE' in tdoc or 'BS' in tdoc:
                    fs_type='BS'
                elif 'FINANCIALSTATEMENTS' in tdoc or 'PL' in tdoc:
                    fs_type='PL'
                else:
                    fs_type=_infer_fs_type(rec, u)
                metrics={k:v for k,v in rec.items() if k not in ('Code','code','Ticker','ticker')}
                out_rows.append({
                    'code': code4,
                    'ticker': f'{code4}.T',
                    'period_end': per,
                    'q_flag': qflag,
                    'fs_type': fs_type,
                    'metrics': json.dumps(metrics, ensure_ascii=False),
                    'source': 'jquants',
                })
            if out_rows:
                return pd.DataFrame(out_rows)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chunk', default=None, help="'next' to process next chunk or integer start index")
    ap.add_argument('--chunk-size', type=int, default=100)
    ap.add_argument('--codes', default=None, help='comma-separated code4 list (e.g., 7203,6501,6758)')
    ap.add_argument('--verbose', action='store_true')
    args = ap.parse_args()

    codes=load_universe()
    if not codes:
        print(json.dumps({'fin_ok':0,'fin_fail':0,'note':'no_universe'}, ensure_ascii=False)); return

    # compute code list to run (resume-safe chunking)
    to_run = list(codes)
    if args.codes:
        sel=[]
        for tok in str(args.codes).split(','):
            tok=tok.strip().upper()
            m=re.fullmatch(r'(\d{4})', tok)
            if not m:
                m=re.fullmatch(r'(\d{4})\.T', tok)
            if m:
                sel.append(m.group(1))
        to_run = sel
    if args.chunk is not None:
        CUR.parent.mkdir(parents=True, exist_ok=True)
        cur = {}
        if CUR.exists():
            try:
                cur = json.loads(CUR.read_text(encoding='utf-8'))
            except Exception:
                cur = {}
        # set or refresh order when codes change
        order = cur.get('order')
        if not order or set(order) != set(codes):
            order = list(codes)
            cur = {'order': order, 'idx': 0}
        idx = cur.get('idx', 0)
        if args.chunk != 'next':
            try:
                idx = max(0, int(args.chunk))
            except Exception:
                idx = 0
        start = int(idx)
        end = min(start + int(args.chunk_size), len(order))
        to_run = order[start:end]
        # advance cursor (wrap)
        cur['idx'] = 0 if end >= len(order) else end
        CUR.write_text(json.dumps(cur), encoding='utf-8')

    ok=fail=0; samples=[]; fail_reasons={}
    for i,c4 in enumerate(to_run,1):
        outp=OUTDIR/f'{c4}.parquet'
        if outp.exists():
            ok+=1; continue
        df=jq_fetch_fin_q(c4, FROM_DEFAULT, TO_DEFAULT, tries=6, stats=fail_reasons, verbose=bool(args.verbose))
        if df is None:
            fail+=1
        else:
            # merge if exists
            if outp.exists():
                try:
                    old=pd.read_parquet(outp)
                    df=pd.concat([old,df], ignore_index=True)
                    df=df.drop_duplicates(['ticker','period_end','fs_type','q_flag'], keep='last')
                except Exception:
                    pass
            df.to_parquet(outp, index=False); ok+=1
            if len(samples)<3:
                samples.append({'code': c4, 'rows': int(len(df))})
        if i%40==0:
            time.sleep(0.5)
    print(json.dumps({'fin_ok': ok, 'fin_fail': fail, 'codes_tried': len(to_run), 'universe': len(codes), 'fail_reasons': fail_reasons}, ensure_ascii=False))


if __name__=='__main__':
    main()

