import numpy as np, pandas as pd, json
from pathlib import Path
P=Path("data/proc/dataset/tdnet_panel.parquet"); PX=Path("data/proc/prices/jp_prices_std.parquet")
OUT=Path("data/proc/labels/targets.parquet"); OUT.parent.mkdir(parents=True, exist_ok=True)
if not P.exists(): print(json.dumps({"targets_rows":0},ensure_ascii=False)); raise SystemExit()
panel=pd.read_parquet(P); px=pd.read_parquet(PX)
panel["eff_date"]=pd.to_datetime(panel["eff_date"]); px["date"]=pd.to_datetime(px["date"])
def y2x(pr,t0,h=252):
    fut=pr[pr["date"]>=t0]
    if len(fut)<h+1: return np.nan
    p0=fut.iloc[0]["adj_close"]; mx=fut.iloc[1:h+1]["adj_close"].max()
    return float(mx>=2*p0)
rows=[]
for tk,g in panel.groupby("ticker", sort=True):
    pr=px[px["ticker"]==tk][["date","adj_close"]].sort_values("date").reset_index(drop=True)
    if pr.empty: continue
    for _,r in g.iterrows():
        y=y2x(pr, r["eff_date"])
        if not np.isnan(y): rows.append({"ticker":tk,"date":r["date"],"y_2x":y})
lab=pd.DataFrame(rows)
if lab.empty: print(json.dumps({"targets_rows":0},ensure_ascii=False)); raise SystemExit()
lab.to_parquet(OUT,index=False)
print(json.dumps({"targets_rows":len(lab),"y2x_rate":float(lab["y_2x"].mean())},ensure_ascii=False))
