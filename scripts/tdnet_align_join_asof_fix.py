import json
import pandas as pd
from pandas.tseries.offsets import BDay
from pathlib import Path

FEAT=Path("data/proc/features_tdnet/tdnet_event_features.parquet")
PX  =Path("data/proc/prices/jp_prices_std.parquet")
OUT =Path("data/proc/dataset/tdnet_panel.parquet")
OUT.parent.mkdir(parents=True, exist_ok=True)

td = pd.read_parquet(FEAT)[["ticker","date","event_strength","novelty","tone_pos","tone_neg","tone_unc","event_cat"]].copy()
px = pd.read_parquet(PX)[["ticker","date","adj_close","volume"]].copy()

td["date"]=pd.to_datetime(td["date"]).dt.normalize()
px["date"]=pd.to_datetime(px["date"]).dt.normalize()

# 価格が存在するティッカーのみ
valid = set(px["ticker"].astype(str).unique())
td = td[td["ticker"].astype(str).isin(valid)].copy()

panels=[]
for tk, g in td.groupby("ticker", sort=True):
    g = g.sort_values("date").copy()
    g["eff_anchor"] = (g["date"] + BDay(1)).dt.normalize()  # T+1寄り基準
    p = px[px["ticker"]==tk].sort_values("date").rename(columns={"date":"px_date"})
    if p.empty: 
        continue
    # forward asof（祝日対応、最大+10暦日まで許容）
    m = pd.merge_asof(g.sort_values("eff_anchor"),
                      p.sort_values("px_date"),
                      left_on="eff_anchor", right_on="px_date",
                      direction="forward", tolerance=pd.Timedelta("10D"))
    m = m.dropna(subset=["px_date","adj_close"]).rename(columns={"px_date":"eff_date"})
    keep=["ticker","date","eff_date","event_strength","novelty","tone_pos","tone_neg","tone_unc","event_cat","adj_close","volume"]
    panels.append(m[keep])

panel = pd.concat(panels, ignore_index=True) if panels else pd.DataFrame(columns=keep)
panel = panel.sort_values(["ticker","date"]).drop_duplicates(["ticker","date","event_cat"])
panel.to_parquet(OUT, index=False)

print(json.dumps({
  "panel_rows": int(len(panel)),
  "tickers": int(panel["ticker"].nunique()) if len(panel) else 0,
  "price_coverage": float(panel["adj_close"].notna().mean()) if len(panel) else 0.0,
  "t_plus_1_span_min": str((panel["eff_date"]-panel["date"]).min()) if len(panel) else None,
  "t_plus_1_span_max": str((panel["eff_date"]-panel["date"]).max()) if len(panel) else None
}, ensure_ascii=False))
