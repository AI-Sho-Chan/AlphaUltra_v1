import json
import pandas as pd
from pathlib import Path

FEAT = Path("data/proc/features_tdnet/tdnet_event_features.parquet")
PX   = Path("data/proc/prices/jp_prices_std.parquet")
OUT  = Path("data/proc/dataset/tdnet_panel.parquet")
OUT.parent.mkdir(parents=True, exist_ok=True)

td = pd.read_parquet(FEAT)
px = pd.read_parquet(PX)

td["eff_date"] = pd.to_datetime(td["eff_date"]).dt.normalize()
px["date"]     = pd.to_datetime(px["date"]).dt.normalize()

# 価格が存在するティッカーだけに限定（偽ティッカー除外）
valid = set(px["ticker"].astype(str).unique())
td = td[td["ticker"].astype(str).isin(valid)]

# 必要列だけ取り出し
cols_feat = ["ticker","eff_date","event_strength","novelty","tone_pos","tone_neg","tone_unc","event_cat"]
td = td[cols_feat].drop_duplicates()

# eff_date(=T+1) に価格を結合
panel = td.merge(px[["ticker","date","adj_close","volume"]],
                 left_on=["ticker","eff_date"], right_on=["ticker","date"], how="left")

# 学習アンカーは eff_date（T+1寄り）
panel["date"] = panel["eff_date"]
panel = panel[["ticker","date","eff_date","event_strength","novelty","tone_pos","tone_neg","tone_unc","event_cat","adj_close","volume"]]
panel = panel.sort_values(["ticker","date"]).reset_index(drop=True)

panel.to_parquet(OUT, index=False)

print({
  "panel_rows": int(len(panel)),
  "tickers": int(panel["ticker"].nunique()),
  "price_coverage": float(panel["adj_close"].notna().mean())
})
