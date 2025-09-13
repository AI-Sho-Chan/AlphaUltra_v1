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

# 価格がある銘柄のみ
valid=set(px["ticker"].astype(str).unique())
td=td[td["ticker"].astype(str).isin(valid)].copy()

# T+1寄りのアンカー
td["eff_anchor"]=(td["date"]+BDay(1)).dt.normalize()

# asof用に完全ソート
td=td.sort_values(["ticker","eff_anchor"])
px=px.sort_values(["ticker","date"]).rename(columns={"date":"px_date"})

# 同一ticker内で forward asof（祝日対応, 最大+10日）
m=pd.merge_asof(td, px, left_on="eff_anchor", right_on="px_date", by="ticker",
                direction="forward", tolerance=pd.Timedelta("10D"))

# 安全網：ticker列がサフィックス化していたら戻す
if "ticker" not in m.columns:
    if "ticker_x" in m.columns: m["ticker"]=m["ticker_x"]
    elif "ticker_y" in m.columns: m["ticker"]=m["ticker_y"]

m=m.dropna(subset=["px_date","adj_close"]).rename(columns={"px_date":"eff_date"})

keep=["ticker","date","eff_date","event_strength","novelty","tone_pos","tone_neg","tone_unc","event_cat","adj_close","volume"]
panel=m[keep].sort_values(["ticker","date"]).drop_duplicates(["ticker","date","event_cat"]).reset_index(drop=True)

panel.to_parquet(OUT, index=False)
print(json.dumps({
  "panel_rows": int(len(panel)),
  "tickers": int(panel["ticker"].nunique()) if len(panel) else 0,
  "price_coverage": float(panel["adj_close"].notna().mean()) if len(panel) else 0.0,
  "date_min": str(panel["date"].min().date()) if len(panel) else None,
  "date_max": str(panel["date"].max().date()) if len(panel) else None
}, ensure_ascii=False))
