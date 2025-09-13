import json
from pathlib import Path
import pandas as pd, numpy as np
from pandas.tseries.offsets import BDay

events_path = Path(r"C:\AI\AlphaUltra_v1\data\proc\features_tdnet\tdnet_event_features.parquet")
prices_path = Path(r"C:\AI\AlphaUltra_v1\data\proc\prices\jp_prices.parquet")
out_panel   = Path(r"C:\AI\AlphaUltra_v1\data\proc\dataset\tdnet_panel.parquet")
out_targets = Path(r"C:\AI\AlphaUltra_v1\data\proc\labels\targets.parquet")
out_panel.parent.mkdir(parents=True, exist_ok=True)
out_targets.parent.mkdir(parents=True, exist_ok=True)

ev = pd.read_parquet(events_path)
px = pd.read_parquet(prices_path)
ev["date"] = pd.to_datetime(ev["date"])
ev["eff_date"] = (ev["date"] + BDay(1)).dt.normalize()
px["date"] = pd.to_datetime(px["date"])
px = px.sort_values(["ticker","date"])[["ticker","date","adj_close"]]

def y2x_label(pr, t_eff, horizon=252):
    fut = pr[pr["date"] >= t_eff]
    if len(fut) < horizon+1:
        return np.nan
    p0 = fut.iloc[0]["adj_close"]
    mx = fut.iloc[1:horizon+1]["adj_close"].max()
    return float(mx >= 2.0*p0)

t_rows=[]
for t, g in ev.groupby("ticker"):
    pr = px[px["ticker"]==t][["date","adj_close"]].reset_index(drop=True)
    if pr.empty: 
        continue
    for _, r in g.sort_values("date").iterrows():
        y = y2x_label(pr, r["eff_date"])
        if np.isnan(y): 
            continue
        t_rows.append({"ticker":t, "date":r["date"], "y_2x":y})

panel = ev.copy()
panel.to_parquet(out_panel.as_posix(), index=False)
tar = pd.DataFrame(t_rows)
tar.to_parquet(out_targets.as_posix(), index=False)

res = {
    "panel_rows": int(len(panel)),
    "targets_rows": int(len(tar)),
    "positives": None if tar.empty else int(tar["y_2x"].sum()),
    "target_rate": None if tar.empty else float(tar["y_2x"].mean()),
    "tickers": int(panel["ticker"].nunique()),
    "date_min": str(panel["date"].min().date()) if len(panel) else None,
    "date_max": str(panel["date"].max().date()) if len(panel) else None
}
print(json.dumps(res, ensure_ascii=False))
