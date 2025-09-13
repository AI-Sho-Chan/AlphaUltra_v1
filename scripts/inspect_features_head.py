import pandas as pd
from pathlib import Path

p=Path('data/proc/features_tdnet/tdnet_event_features.parquet')
d=pd.read_parquet(p)
print('rows', len(d))
print('cols', list(d.columns))
dc=pd.to_datetime(d['date'], errors='coerce')
print('date_min', str(dc.min().date()) if len(dc)>0 else None)
print('date_max', str(dc.max().date()) if len(dc)>0 else None)
print('sample', d.head(3).to_dict(orient='records'))

