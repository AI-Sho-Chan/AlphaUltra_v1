import pandas as pd
from pathlib import Path

p = Path('data/proc/prices/jp_prices_std.parquet')
px = pd.read_parquet(p)
px['date'] = pd.to_datetime(px['date'], errors='coerce').dt.normalize()
px = px.dropna(subset=['ticker','date','adj_close'])
print('rows', len(px))
print('date_min', str(px['date'].min().date()))
print('date_max', str(px['date'].max().date()))
print('ticker_example', str(px['ticker'].astype(str).iloc[0]))
print('unique_tickers', int(px['ticker'].nunique()))

