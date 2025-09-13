import json
from pathlib import Path
import pandas as pd

panel_path = Path(r"C:\AI\AlphaUltra_v1\data\proc\dataset\tdnet_panel.parquet")
labels_path = Path(r"C:\AI\AlphaUltra_v1\data\proc\labels\targets.parquet")
prices_path = Path(r"C:\AI\AlphaUltra_v1\data\proc\prices\jp_prices.parquet")

df = pd.read_parquet(panel_path)
y  = pd.read_parquet(labels_path) if labels_path.exists() else pd.DataFrame()
px = pd.read_parquet(prices_path) if prices_path.exists() else pd.DataFrame(columns=["ticker","date","adj_close"])

# 型整備
df["date"] = pd.to_datetime(df["date"], errors="coerce")
if "eff_date" in df.columns:
    df["eff_date"] = pd.to_datetime(df["eff_date"], errors="coerce")
px["date"] = pd.to_datetime(px["date"], errors="coerce")

# 欠損
na_top10 = df.isna().mean().sort_values(ascending=False).head(10).to_dict()

# T+1整合
t1_viol = None
if "eff_date" in df.columns:
    t1_viol = int(((df["eff_date"] <= df["date"]) | df["eff_date"].isna()).sum())

# 価格被覆率（eff_date以降に価格が1件でもあるか）
def has_px(row):
    t = row["ticker"]
    ed = row["eff_date"] if "eff_date" in df.columns else row["date"]
    sub = px[(px["ticker"]==t) & (px["date"]>=ed)]
    return len(sub) > 0
px_cov = float(df.apply(has_px, axis=1).mean()) if not px.empty else 0.0

# 年別件数
by_year = df["date"].dt.year.value_counts().sort_index().to_dict()

res = {
  "panel_shape": [int(df.shape[0]), int(df.shape[1])],
  "tickers": int(df["ticker"].nunique()),
  "date_min": None if df.empty else str(df["date"].min().date()),
  "date_max": None if df.empty else str(df["date"].max().date()),
  "na_top10": na_top10,
  "t_plus_1_violations": t1_viol,
  "price_coverage": px_cov,
  "labels_rows": int(len(y)),
  "y2x_rate": None if y.empty or "y_2x" not in y.columns else float(y["y_2x"].mean()),
  "year_counts": by_year
}
print(json.dumps(res, ensure_ascii=False))
