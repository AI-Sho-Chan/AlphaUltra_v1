import pandas as pd, json
from pathlib import Path

FEAT = Path("data/proc/features_tdnet/tdnet_event_features.parquet")
PX   = Path("data/proc/prices/jp_prices_std.parquet")
OUT  = Path("data/proc/dataset/tdnet_panel.parquet")
OUT.parent.mkdir(parents=True, exist_ok=True)

td = pd.read_parquet(FEAT)
px = pd.read_parquet(PX)

# 正規化
td["date"] = pd.to_datetime(td["date"]).dt.normalize()
px["date"] = pd.to_datetime(px["date"]).dt.normalize()

# 価格がある銘柄だけに限定（偽ティッカー除去）
valid = set(px["ticker"].astype(str).unique())
td = td[td["ticker"].astype(str).isin(valid)].copy()

# asof forward（同一ticker内で、イベント日以後の最初の価格日を拾う）
td = td.sort_values(["ticker","date"])
px2 = px.sort_values(["ticker","date"]).rename(columns={"date":"px_date"})
m = pd.merge_asof(td, px2, left_on="date", right_on="px_date", by="ticker",
                  direction="forward", tolerance=pd.Timedelta("10D"))

# eff_date = px側の日付。イベント日 'date' は上書きしない
m = m.rename(columns={"px_date":"eff_date"})

# 必要列
keep = ["ticker","date","eff_date","event_strength","novelty","tone_pos","tone_neg","tone_unc","event_cat","adj_close","volume"]
panel = m[keep].dropna(subset=["eff_date"]).sort_values(["ticker","date"]).reset_index(drop=True)

panel.to_parquet(OUT, index=False)
print(json.dumps({
  "panel_rows": int(len(panel)),
  "tickers": int(panel["ticker"].nunique()),
  "price_coverage": float(panel["adj_close"].notna().mean()),
  "date_min": str(panel["date"].min().date()) if len(panel) else None,
  "date_max": str(panel["date"].max().date()) if len(panel) else None
}, ensure_ascii=False))
