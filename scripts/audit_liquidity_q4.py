# scripts/audit_liquidity_q4.py
import json, pandas as pd, pathlib, re
from pathlib import Path
cv = json.loads(Path("reports/cv_t5_y_2x_v2.json").read_text())
ts = pd.to_datetime(cv["folds"][0]["test_start"]); te = pd.to_datetime(cv["folds"][0]["test_end"])
feat_path = "data/proc/features_tdnet/tdnet_event_features.parquet"
m = re.search(r"tdnet_features\s*:\s*(.+)", Path("configs/tdnet_2014.yaml").read_text(encoding="utf-8"))
if m: feat_path = m.group(1).strip()
fe = pd.read_parquet(feat_path, columns=["ticker","eff_date"])
fe["eff_date"]=pd.to_datetime(fe["eff_date"]).dt.tz_localize(None)
fe_q4 = fe[(fe["eff_date"]>=ts)&(fe["eff_date"]<=te)].copy()

pr = pd.read_parquet("data/proc/adj_prices/adj_prices.parquet", columns=["ticker","date","adj_close","addv_3m"])
pr["date"]=pd.to_datetime(pr["date"]).dt.tz_localize(None)
# eff_date → その銘柄の次の取引日に前方結合
fe_q4 = fe_q4.sort_values(["ticker","eff_date"])
pr = pr.sort_values(["ticker","date"])
merged = pd.merge_asof(
    fe_q4, pr, left_on="eff_date", right_on="date",
    by="ticker", direction="forward", allow_exact_matches=True
)
liq = (merged["adj_close"]>=200) & (merged["addv_3m"]>=1e8)
out = {
  "events_q4": int(len(fe_q4)),
  "with_price": int(merged["adj_close"].notna().sum()),
  "liquidity_pass": int(liq.sum()),
  "pass_rate": float((liq.mean() if len(merged)>0 else 0.0))
}
print(json.dumps(out, ensure_ascii=False))
