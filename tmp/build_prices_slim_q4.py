import pathlib, pandas as pd, json

# 入力
chosen = json.loads(pathlib.Path("tmp/chosen_prices.json").read_text(encoding="utf-8"))["chosen"]
prices = pathlib.Path(chosen)
features = pathlib.Path("data/proc/features_tdnet/tdnet_event_features.parquet")

# 期間（Q4検証最小化）
win_lo = pd.Timestamp("2013-11-01")
win_hi = pd.Timestamp("2014-12-31")

# 特徴側から対象銘柄と日付キーを抽出
fe = pd.read_parquet(features, columns=["ticker","eff_date"])
fe["eff_date"] = pd.to_datetime(fe["eff_date"])
fe = fe[(fe["eff_date"]>=win_lo) & (fe["eff_date"]<=win_hi)]
tickers = fe["ticker"].dropna().unique().tolist()

# 価格読み込みフィルタ
use_cols = ["ticker","date","adj_close","volume","addv_3m"]
px = pd.read_parquet(prices)
for c0,c1 in (("Adj Close","adj_close"),("adjclose","adj_close"),("px_close","adj_close")):
    if "adj_close" not in px.columns and c0 in px.columns:
        px["adj_close"] = px[c0]
if "adj_close" not in px.columns:
    raise SystemExit({"error":"adj_close missing", "cols": list(px.columns)[:20]})

px["date"] = pd.to_datetime(px["date"])
px = px[px["date"].between(win_lo, win_hi)]
if tickers:
    px = px[px["ticker"].isin(tickers)]

# 必要列だけに絞る＋無い列は作る
keep = [c for c in use_cols if c in px.columns]
px = px[["ticker","date"]+keep] if keep else px[["ticker","date","adj_close","volume"]]
if "volume" not in px.columns: px["volume"] = 0
if "addv_3m" not in px.columns: px["addv_3m"] = pd.NA

# 結合キー合わせ
px = px.drop_duplicates(["ticker","date"]).copy()
px["eff_date"] = px["date"]

# 型ダウンサイジング
px["ticker"] = px["ticker"].astype("category")
for c in ("adj_close","addv_3m"):
    if c in px.columns: px[c] = pd.to_numeric(px[c], errors="coerce").astype("float32")
px["volume"] = pd.to_numeric(px["volume"], errors="coerce").fillna(0).astype("int32")

out = pathlib.Path("data/proc/prices/jp_prices_std_compat_slim_q4.parquet")
out.parent.mkdir(parents=True, exist_ok=True)
px.to_parquet(out, index=False)

print({
  "out": str(out),
  "rows": len(px),
  "cols": list(px.columns),
  "date_min": str(px["date"].min()),
  "date_max": str(px["date"].max()),
  "tickers": len(px["ticker"].cat.categories) if hasattr(px["ticker"],"cat") else px["ticker"].nunique()
})
