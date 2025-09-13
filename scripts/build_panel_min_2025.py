import json, numpy as np, pandas as pd, pathlib as P
feat=P.Path("data/proc/features_tdnet/tdnet_event_features.parquet")
pxs =P.Path("data/proc/prices/jp_prices_std.parquet")
out =P.Path("data/proc/dataset/tdnet_panel.parquet"); out.parent.mkdir(parents=True, exist_ok=True)
td=pd.read_parquet(feat,columns=["ticker","date","event_strength","novelty","tone_pos","tone_neg","tone_unc","event_cat"])
td["date"]=pd.to_datetime(td["date"])
td=td[(td["ticker"]=="7203.T")&(td["date"]>="2025-06-01")&(td["date"]<="2025-08-31")].sort_values(["ticker","date"])
px=pd.read_parquet(pxs,columns=["ticker","date","adj_close","volume"]); px["date"]=pd.to_datetime(px["date"])
p=px[px["ticker"]=="7203.T"].sort_values("date").reset_index(drop=True)
panels=[]
if not td.empty and not p.empty:
  p_dates=p["date"].to_numpy("datetime64[ns]")
  idx=np.searchsorted(p_dates, td["date"].to_numpy("datetime64[ns]"), side="right")
  ok=idx<len(p_dates)
  if ok.any():
    g=td.loc[ok].copy()
    g["eff_date"]=pd.to_datetime(p_dates[idx[ok]])
    g=g.merge(p.rename(columns={"date":"eff_date"}), on=["ticker","eff_date"], how="left")
    panels.append(g)
cols=["ticker","date","eff_date","event_strength","novelty","tone_pos","tone_neg","tone_unc","event_cat","adj_close","volume"]
panel=(pd.concat(panels,ignore_index=True) if panels else pd.DataFrame(columns=cols))
panel=panel[cols].dropna(subset=["adj_close"]).sort_values(["ticker","date"]).drop_duplicates(["ticker","date","event_cat"])
panel.to_parquet(out,index=False)
print(json.dumps({"panel_rows":len(panel),"price_coverage":(float(panel["adj_close"].notna().mean()) if len(panel) else 0.0)},ensure_ascii=False))
