import json
from pathlib import Path
import pandas as pd
from pandas.tseries.offsets import BDay

p=Path('data/proc/dataset/tdnet_panel.parquet')
df=pd.read_parquet(p)
added=False
if 'eff_date' not in df.columns:
    df['date']=pd.to_datetime(df['date'])
    df['eff_date']=(df['date']+BDay(1)).dt.normalize()
    added=True

viol=int((df['eff_date']<=df['date']).sum()) if 'eff_date' in df.columns else -1
info={'added_eff_date':added,'rows':int(len(df)),
      'min_date':str(pd.to_datetime(df['date']).min().date()),
      'max_date':str(pd.to_datetime(df['date']).max().date()),
      'min_eff':str(pd.to_datetime(df['eff_date']).min().date()) if 'eff_date' in df.columns else None,
      'max_eff':str(pd.to_datetime(df['eff_date']).max().date()) if 'eff_date' in df.columns else None,
      't+1_violations':int(viol)}

# 上書き保存（初回のみ）
if added:
    bak=p.with_suffix('.bak.parquet')
    p.replace(bak)
    df.to_parquet(p,index=False)

print(json.dumps(info, ensure_ascii=False))
