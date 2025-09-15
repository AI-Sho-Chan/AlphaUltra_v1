# scripts/promote_jp_prices_std_v2.py
import json
from pathlib import Path
import pandas as pd
src = Path("data/proc/prices/jp_prices_std.parquet")
dst = Path("data/proc/adj_prices/adj_prices.parquet")
df = pd.read_parquet(src)
cols = {c.lower(): c for c in df.columns}
# 基本列
close = df[cols.get("adj_close") or cols.get("close")].rename("adj_close")
date  = pd.to_datetime(df[cols.get("date")]).dt.tz_localize(None)
tic   = df[cols.get("ticker")].astype(str)
# 体積 × 価格 → ADDV（なければ作る）
if "addv_3m" in cols:
    addv3 = df[cols["addv_3m"]].astype("float64")
else:
    vol = df[cols.get("volume")] if cols.get("volume") else None
    if vol is None:
        raise SystemExit(json.dumps({"error":"no_volume_in_source"}, ensure_ascii=False))
    addv = vol.astype("float64") * close.astype("float64")
    addv3 = addv.groupby(tic).rolling(63, min_periods=1).mean().reset_index(level=0, drop=True)
out = pd.DataFrame({"ticker": tic, "date": date, "adj_close": close, "addv_3m": addv3})
out = out.sort_values(["ticker","date"]).dropna(subset=["adj_close"])
dst.parent.mkdir(parents=True, exist_ok=True)
out.to_parquet(dst, index=False)
print(json.dumps({
  "written": str(dst), "rows": int(len(out)),
  "tickers": int(out["ticker"].nunique()),
  "date_min": str(out["date"].min().date()),
  "date_max": str(out["date"].max().date()),
  "addv3_na_rate": float(out["addv_3m"].isna().mean())
}, ensure_ascii=False))
