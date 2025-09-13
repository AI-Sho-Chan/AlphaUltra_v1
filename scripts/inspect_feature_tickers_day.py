import re
import sys
from pathlib import Path
import pandas as pd

day = sys.argv[1] if len(sys.argv) > 1 else '2014-11-14'
p=Path('data/proc/features_tdnet/tdnet_event_features.parquet')
d=pd.read_parquet(p, columns=['ticker','date'])
d['date']=pd.to_datetime(d['date'], errors='coerce')
sel=d.loc[d['date'].dt.date==pd.Timestamp(day).date(),'ticker'].astype(str)
uniq=sorted(set(sel))
valid=[x for x in uniq if re.fullmatch(r'[1-9]\d{3}\.T', x)]
print({'day': day, 'total': len(uniq), 'valid': len(valid)})
print('valid_sample', valid[:20])

