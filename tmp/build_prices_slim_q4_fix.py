import pathlib, pandas as pd, json, numpy as np

chosen = json.loads(pathlib.Path("tmp/chosen_prices.json").read_text(encoding="utf-8"))["chosen"]
prices = pathlib.Path(chosen)
features = pathlib.Path("data/proc/features_tdnet/tdnet_event_features.parquet")

win_lo = pd.Timestamp("2013-11-01")
win_hi = pd.Timestamp("2014-12-31")

fe = pd.read_parquet(features, columns=["ticker","eff_date"])
fe["eff_date"] = pd.to_datetime(fe["eff_date"])
fe = fe[(fe["eff_date"]>=win_lo) & (fe["eff_date"]<=win_hi)]
tickers = fe["ticker"].dropna().unique().tolist()

px = pd.read_parquet(prices)

# 1) 列名を正規化しつつ重複名を除去（先勝ち）
orig_cols = list(px.columns)
px.columns = [str(c) for c in px.columns]               # 文字列化
dup_mask = px.columns.duplicated(keep="first")
if dup_mask.any():
    px = px.loc[:, ~dup_mask]

# 2) date列を特定（候補順に探索）
date_candidates = [c for c in ["date","Date","trade_date","dt"] if c in px.columns]
if not date_candidates:
    # 識別できない場合、日付型列から最初の1つを採用
    cand = [c for c in px.columns if np.issubdtype(px[c].dtype, np.datetime64)]
    if not cand:
        raise SystemExit({"error":"no date-like column", "cols": orig_cols[:30]})
    date_col = cand[0]
else:
    date_col = date_candidates[0]

# 3) adj_close 補完
if "adj_close" not in px.columns:
    for c in ("px_close","close","Adj Close","adjclose","adjusted_close","adjClose"):
        if c in px.columns:
            px["adj_close"] = px[c]; break
if "adj_close" not in px.columns:
    raise SystemExit({"error":"adj_close missing", "cols": list(px.columns)[:30]})

# 4) 必要期間・銘柄で絞り込み
px[date_col] = pd.to_datetime(px[date_col])
px = px[px[date_col].between(win_lo, win_hi)]
if tickers:
    px = px[px["ticker"].isin(tickers)]

# 5) volume/ addv_3m 整備
if "volume" not in px.columns:
    for v in ("vol","Volume","volume_adj"):
        if v in px.columns:
            px["volume"] = px[v]; break
if "volume" not in px.columns:
    px["volume"] = 0

if "addv_3m" not in px.columns:
    px["addv_3m"] = pd.NA

# 6) 結合キー作成と重複排除
px = px.drop_duplicates(["ticker", date_col]).copy()
px["eff_date"] = px[date_col]

# 7) 型ダウンサイジング
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
  "date_col": date_col,
  "date_min": str(px["eff_date"].min()),
  "date_max": str(px["eff_date"].max()),
  "tickers": px["ticker"].nunique()
})
