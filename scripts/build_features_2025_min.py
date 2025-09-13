import json, re, pandas as pd
from pandas.tseries.offsets import BDay
from pathlib import Path

RAW = Path("data/raw/tdnet")
OUT = Path("data/proc/features_tdnet/tdnet_event_features.parquet")
OUT.parent.mkdir(parents=True, exist_ok=True)

rows=[]
for p in RAW.rglob("*.json"):
    m=re.search(r"(20\d{2})[\\/](\d{2})[\\/](\d{2})", str(p))
    if not m: 
        continue
    d="-".join(m.groups())
    if not ("2025-06-01" <= d <= "2025-08-31"):
        continue
    try:
        j=json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        continue
    t=j.get("ticker")
    dt=pd.to_datetime(j.get("date") or d, errors="coerce")
    if not t or pd.isna(dt):
        continue
    et=str(j.get("event_type") or "other")
    pos={"guidance_up","div_up","buyback","order","product","earnings"}
    neg={"guidance_down","div_down","offering","lawsuit"}
    rows.append({
        "ticker": t, "date": dt.normalize(), "event_type": et, "event_cat": et,
        "event_strength": 1.0, "novelty": 0.0,
        "tone_pos": int(et in pos), "tone_neg": int(et in neg), "tone_unc": 0
    })

df = pd.DataFrame(rows).drop_duplicates(["ticker","date","event_type"])
if df.empty:
    print({"features_rows": 0}); raise SystemExit()
df["eff_date"] = (df["date"] + BDay(1)).dt.normalize()
df.to_parquet(OUT, index=False)
print({"features_rows": int(len(df)), "tickers": int(df["ticker"].nunique())})
