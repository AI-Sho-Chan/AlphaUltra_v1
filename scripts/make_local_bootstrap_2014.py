#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
import pandas as pd


def main():
    feat = Path('data/proc/features_tdnet/tdnet_event_features.parquet')
    outp = Path('data/local_bootstrap/prices_2014.csv')
    outp.parent.mkdir(parents=True, exist_ok=True)
    d = pd.read_parquet(feat, columns=['ticker', 'date']).dropna()
    d['date'] = pd.to_datetime(d['date'], errors='coerce')
    d = d[(d['date'] >= '2014-01-01') & (d['date'] <= '2014-12-31')].dropna()
    tickers = sorted(d['ticker'].astype(str).str.upper().unique().tolist())
    days = pd.bdate_range('2014-01-01', '2014-12-31')

    frames = []
    for t in tickers:
        # deterministic pseudo-price per ticker
        base = 50.0 + (hash(t) % 5000) / 100.0
        px = pd.DataFrame({
            'ticker': t,
            'date': days,
            'adj_close': base,
            'volume': 100000
        })
        frames.append(px)
    allpx = pd.concat(frames, ignore_index=True)
    allpx.to_csv(outp, index=False, encoding='utf-8')
    print({'bootstrap_rows': int(len(allpx)), 'tickers': len(tickers), 'out': str(outp)})


if __name__ == '__main__':
    main()

