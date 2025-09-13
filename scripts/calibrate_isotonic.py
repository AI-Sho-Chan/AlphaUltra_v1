import argparse, json, numpy as np, pandas as pd
from sklearn.isotonic import IsotonicRegression
ap=argparse.ArgumentParser(); ap.add_argument('--input'); ap.add_argument('--ppv_target', type=float, default=0.8); a=ap.parse_args()
r=json.load(open(a.input,'r',encoding='utf-8'))
oof=pd.DataFrame(r['oof_predictions'])
y=oof['y'].values; p=oof['p'].values
iso=IsotonicRegression(out_of_bounds='clip').fit(p,y)
pc=iso.transform(p)
best=None
for th in np.linspace(pc.min(), pc.max(), 401):
    sel=pc>=th
    if sel.sum()==0: continue
    ppv=y[sel].mean(); cov=sel.mean()
    if ppv>=a.ppv_target and (best is None or th<best[0]): best=(th,ppv,cov)
print({'thr':None if best is None else float(best[0]), 'ppv':None if best is None else float(best[1]), 'coverage':0.0 if best is None else float(best[2])})
