#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, re
import pandas as pd
from pathlib import Path

SRC_DIRS = [Path('data/raw/prices'), Path('data/raw/jquants/prices')]
OUT = Path('data/proc/prices'); OUT.mkdir(parents=True, exist_ok=True)
BOOT = Path('data/local_bootstrap/prices_2014.csv')
REPORTS = Path('reports'); REPORTS.mkdir(parents=True, exist_ok=True)


def source_from_name(path: Path) -> str:
    n = path.name.lower()
    if n.startswith('stooq_'): return 'stooq'
    if n.startswith('yf_') or n.startswith('yahoo_'): return 'yahoo'
    if str(path).replace('\\','/').find('/jquants/prices/') >= 0: return 'jquants'
    if n.startswith('jq_') or n.startswith('jquants_') or n.startswith('jquants-'): return 'jquants'
    if n.startswith('eod_') or n.startswith('eodhd_'): return 'eodhd'
    return 'unknown'


frames = []
src_counts = {}

for root in SRC_DIRS:
    if not root.exists():
        continue
    for fp in root.rglob('*.parquet'):
        try:
            d = pd.read_parquet(fp)
        except Exception:
            continue
        cols = {c.lower(): c for c in d.columns}
        # date
        if 'date' in cols:
            dt = pd.to_datetime(d[cols['date']], errors='coerce')
            if hasattr(dt.dt, 'tz') and dt.dt.tz is not None:
                dt = dt.dt.tz_convert(None).dt.normalize()
            else:
                dt = dt.dt.normalize()
        elif d.index.name and str(d.index.dtype).startswith('datetime'):
            dt = pd.to_datetime(d.index, errors='coerce').tz_localize(None).normalize()
        else:
            continue
        # ticker
        if 'ticker' in cols:
            tk = d[cols['ticker']].astype(str)
        elif 'symbol' in cols:
            tk = d[cols['symbol']].astype(str)
        else:
            m = re.search(r'(\d{4}\.T)', fp.name)
            if not m:
                continue
            tk = pd.Series([m.group(1)] * len(d))
        # price
        ac = None
        for k in ['adj_close','adjusted close','adjusted_close','adj close']:
            if k in cols:
                ac = pd.to_numeric(d[cols[k]], errors='coerce'); break
        if ac is None and 'close' in cols:
            ac = pd.to_numeric(d[cols['close']], errors='coerce')
        if ac is None:
            continue
        vol = pd.to_numeric(d[cols['volume']], errors='coerce') if 'volume' in cols else None
        src = d['source'].mode().iloc[0] if 'source' in d.columns and not d['source'].mode().empty else source_from_name(fp)
        src_counts[src] = src_counts.get(src, 0) + int(len(d))
        frames.append(pd.DataFrame({'date': dt, 'ticker': tk, 'adj_close': ac, 'volume': vol, 'source': src}))

# Local bootstrap
if BOOT.exists():
    try:
        b = pd.read_csv(BOOT)
        cols = {c.lower(): c for c in b.columns}
        if {'ticker','date','adj_close'}.issubset(cols.keys()):
            bdf = pd.DataFrame({
                'date': pd.to_datetime(b[cols['date']], errors='coerce').dt.normalize(),
                'ticker': b[cols['ticker']].astype(str),
                'adj_close': pd.to_numeric(b[cols['adj_close']], errors='coerce'),
                'volume': pd.to_numeric(b.get(cols.get('volume'))) if cols.get('volume') else None,
                'source': 'bootstrap',
            }).dropna(subset=['date','ticker','adj_close']).reset_index(drop=True)
            if not bdf.empty:
                src_counts['bootstrap'] = src_counts.get('bootstrap',0) + int(len(bdf))
                frames.append(bdf)
    except Exception:
        pass

if not frames:
    print(json.dumps({'rows':0}, ensure_ascii=False)); raise SystemExit

px = (pd.concat(frames, ignore_index=True)
        .dropna(subset=['date','ticker','adj_close'])
        .sort_values(['ticker','date'])
        .drop_duplicates(['ticker','date'], keep='first'))

px.to_parquet(OUT/'jp_prices_std.parquet', index=False)
log = {'std_rows': int(len(px)), 'tickers': int(px['ticker'].nunique()), 'date_min': str(px['date'].min().date()), 'date_max': str(px['date'].max().date()), 'sources': {k:int(v) for k,v in sorted(src_counts.items())}}
print(json.dumps(log, ensure_ascii=False))
(REPORTS/'price_std_build.log').write_text(json.dumps(log, ensure_ascii=False)+'\n', encoding='utf-8')

