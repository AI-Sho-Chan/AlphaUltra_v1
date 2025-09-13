import argparse, pandas as pd
ap=argparse.ArgumentParser(); ap.add_argument('--panel'); ap.add_argument('--labels'); a=ap.parse_args()
df=pd.read_parquet(a.panel); y=pd.read_parquet(a.labels)
print('panel', df.shape, 'targets', y.shape)
print('cols_sample', sorted(df.columns)[:40])
print('na_top10', df.isna().mean().sort_values(ascending=False).head(10).to_dict())
if 'y_2x' in y: print('target_rate_y_2x', float(y['y_2x'].mean()))
if {'date','eff_date'}.issubset(df.columns):
    bad=(df['eff_date']<=df['date']).sum(); print('t+1_violations', int(bad))
