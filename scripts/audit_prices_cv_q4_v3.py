# scripts/audit_prices_cv_q4_v3.py
import json, yaml
from pathlib import Path
import pandas as pd

cv = json.loads(Path("reports/cv_t5_y_2x_v2.json").read_text(encoding="utf-8"))
ts = pd.to_datetime(cv["folds"][0]["test_start"]); te = pd.to_datetime(cv["folds"][0]["test_end"])

cfg = yaml.safe_load(Path("configs/tdnet_2014.yaml").read_text(encoding="utf-8")) or {}
price_path = cfg.get("paths",{}).get("prices")
df = pd.read_parquet(price_path, columns=["ticker","date","px_close","addv_3m"])
df["date"]=pd.to_datetime(df["date"]).dt.tz_localize(None)
df=df.sort_values(["ticker","date"])
df["idx"]=df.groupby("ticker").cumcount()
mx=df.groupby("ticker")["idx"].transform("max")
df["has_fwd252"]=(mx-df["idx"])>=252

mask=(df["date"]>=ts)&(df["date"]<=te)
liq=(df["addv_3m"]>=1e8)&(df["px_close"]>=200)

probe=df.loc[mask & df["has_fwd252"], ["ticker","date","px_close"]].copy()
# y_2x簡易
g=df.groupby("ticker")["px_close"]
probe["fwdmax"]=g.transform(lambda s: s.iloc[::-1].rolling(252, min_periods=252).max().iloc[::-1])[probe.index]
probe=probe.dropna()
probe["y_2x"]=(probe["fwdmax"]/probe["px_close"]>=2).astype(int)

out={
  "price_file": price_path,
  "val_rows_total": int(mask.sum()),
  "val_rows_with_fwd252": int(len(probe)),
  "val_rows_liq": int((mask & liq).sum()),
  "val_rows_liq_fwd252": int((mask & liq & df["has_fwd252"]).sum()),
  "pos": int(probe["y_2x"].sum()),
  "neg": int((probe["y_2x"]==0).sum())
}
print(json.dumps(out, ensure_ascii=False))
