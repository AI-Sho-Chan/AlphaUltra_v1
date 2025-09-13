import pandas as pd, json
from pathlib import Path
P=Path("data/proc/dataset/tdnet_panel.parquet"); L=Path("data/proc/labels/targets.parquet"); PX=Path("data/proc/prices/jp_prices_std.parquet")
df=pd.read_parquet(P) if P.exists() else pd.DataFrame()
y=pd.read_parquet(L) if L.exists() else pd.DataFrame()
px=pd.read_parquet(PX) if PX.exists() else pd.DataFrame(columns=["ticker","date","adj_close"])
for c in ("date","eff_date"):
    if c in df: df[c]=pd.to_datetime(df[c])
pc=0.0
if not df.empty and not px.empty:
    pc=float(df.merge(px.rename(columns={"date":"eff_date"}), on=["ticker","eff_date"], how="left")["adj_close"].notna().mean())
print(json.dumps({"panel_shape":list(df.shape) if not df.empty else [0,0],
                  "tickers": int(df["ticker"].nunique()) if "ticker" in df else 0,
                  "price_coverage": pc,
                  "labels_rows": int(len(y)) if not y.empty else 0}, ensure_ascii=False))
