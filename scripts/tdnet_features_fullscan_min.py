import json, re
from pathlib import Path
import pandas as pd
from pandas.tseries.offsets import BDay

RAW = Path("data/raw/tdnet")
OUT = Path("data/proc/features_tdnet/tdnet_event_features.parquet")
OUT.parent.mkdir(parents=True, exist_ok=True)

START = pd.to_datetime("2013-09-01")
END   = pd.to_datetime("2024-09-10")

pos = {"guidance_up","div_up","buyback","order","product","earnings"}
neg = {"guidance_down","div_down","offering","lawsuit"}

rows=[]
for fp in RAW.rglob("*.json"):
    try:
        j = json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        continue
    tkr = j.get("ticker") or (str(j.get("code4") or "") + ".T")
    if not tkr or ".T" not in tkr: 
        continue
    d = pd.to_datetime(j.get("date"), errors="coerce")
    if pd.isna(d) or d < START or d > END:
        continue
    et = str(j.get("event_type") or "other")
    rows.append({
        "ticker": tkr,
        "date": d.normalize(),
        "event_type": et,
        "event_strength": 1.0,
        "novelty": 0.0,
        "tone_pos": int(et in pos),
        "tone_neg": int(et in neg),
        "tone_unc": 0,
    })

df = pd.DataFrame(rows)
if df.empty:
    print({"rows":0}); raise SystemExit

df["eff_date"] = (pd.to_datetime(df["date"]) + BDay(1)).dt.normalize()
df["event_cat"] = df["event_type"]

# 必要列のみ、重複除去
keep = ["ticker","date","eff_date","event_strength","novelty","tone_pos","tone_neg","tone_unc","event_cat","event_type"]
df = df[keep].drop_duplicates(subset=["ticker","date","event_type"])

df.to_parquet(OUT, index=False)

print({
  "rows": int(len(df)),
  "tickers": int(df["ticker"].nunique()),
  "date_min": str(df["date"].min().date()),
  "date_max": str(df["date"].max().date())
})
