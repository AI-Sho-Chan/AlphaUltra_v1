# scripts/promote_prices_for_t6.py
import json
from pathlib import Path
import pandas as pd

src = Path("data/proc/adj_prices/adj_prices.parquet")
dst = Path("data/proc/prices/jp_prices_std.parquet")
dst.parent.mkdir(parents=True, exist_ok=True)

need = ["ticker","date","adj_close","addv_3m"]
have = []
for cols in (need, ["ticker","date","px_close","addv_3m"]):
    try:
        pd.read_parquet(src, columns=cols)
        have = cols; break
    except Exception:
        pass
if not have:
    print(json.dumps({"error":"prices_parquet_missing_cols","path":str(src)}, ensure_ascii=False)); raise SystemExit()

df = pd.read_parquet(src, columns=have)
df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
if "px_close" not in df.columns:
    df = df.rename(columns={"adj_close":"px_close"})
df = df[["ticker","date","px_close","addv_3m"]].sort_values(["ticker","date"])
df.to_parquet(dst, index=False)

out = {
  "written": str(dst),
  "rows": int(len(df)),
  "tickers": int(df["ticker"].nunique()),
  "date_min": str(df["date"].min().date()),
  "date_max": str(df["date"].max().date()),
  "cols": list(df.columns),
}
print(json.dumps(out, ensure_ascii=False))
