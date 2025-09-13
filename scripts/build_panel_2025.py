import numpy as np, pandas as pd, json
from pathlib import Path
FEAT=Path("data/proc/features_tdnet/tdnet_event_features.parquet")
PX  =Path("data/proc/prices/jp_prices_std.parquet")
OUT =Path("data/proc/dataset/tdnet_panel.parquet"); OUT.parent.mkdir(parents=True, exist_ok=True)

td=pd.read_parquet(FEAT,columns=["ticker","date","event_strength","novelty","tone_pos","tone_neg","tone_unc","event_cat"])
td["date"]=pd.to_datetime(td["date"])
td=td[(td["date"]>="2025-06-01")&(td["date"]<="2025-08-31")].sort_values(["ticker","date"])

px=pd.read_parquet(PX,columns=["ticker","date","adj_close","volume"]).sort_values(["ticker","date"])
px["date"]=pd.to_datetime(px["date"])

valid=set(px["ticker"].astype(str).unique())
td=td[td["ticker"].astype(str).isin(valid)].reset_index(drop=True)

panels=[]
for tk,g in td.groupby("ticker", sort=True):
    p=px[px["ticker"]==tk].reset_index(drop=True)
    if p.empty: continue
    p_dates=p["date"].to_numpy("datetime64[ns]")
    idx=np.searchsorted(p_dates, g["date"].to_numpy("datetime64[ns]"), side="right")  # > 発表日
    ok=idx<len(p_dates)
    if not ok.any(): continue
    g2=g.loc[ok].copy()
    g2["eff_date"]=pd.to_datetime(p_dates[idx[ok]])                   # T+1取引日
    g2=g2.merge(p.rename(columns={"date":"eff_date"}), on=["ticker","eff_date"], how="left")
    panels.append(g2)

cols=["ticker","date","eff_date","event_strength","novelty","tone_pos","tone_neg","tone_unc","event_cat","adj_close","volume"]
panel=(pd.concat(panels, ignore_index=True) if panels else pd.DataFrame(columns=cols))
panel=panel[cols].dropna(subset=["adj_close"]).sort_values(["ticker","date"]).drop_duplicates(["ticker","date","event_cat"]).reset_index(drop=True)
panel.to_parquet(OUT,index=False)
print(json.dumps({"panel_rows":len(panel),"tickers":panel["ticker"].nunique() if len(panel) else 0,
                  "price_coverage": (float(panel["adj_close"].notna().mean()) if len(panel) else 0.0)},ensure_ascii=False))
