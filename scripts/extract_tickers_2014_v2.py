# -*- coding: utf-8 -*-
import re, json
from pathlib import Path
import pandas as pd
from datetime import datetime

FEAT = Path("data/proc/features_tdnet/tdnet_event_features.parquet")
RAW  = Path("data/raw/tdnet")
OUT  = Path("data/tmp/tickers_2014.csv"); OUT.parent.mkdir(parents=True, exist_ok=True)

tick=set()

# 1) features から 2014 年だけ厳密抽出
if FEAT.exists():
    d=pd.read_parquet(FEAT, columns=["ticker","date"])
    d["date"]=pd.to_datetime(d["date"], errors="coerce")
    win=d[(d["date"]>=pd.Timestamp("2014-01-01")) & (d["date"]<=pd.Timestamp("2014-12-31"))]
    for t in win["ticker"].astype(str).unique():
        if re.match(r"^\d{4}\.T$", t): tick.add(t)

# 2) 念のため raw tdnet の 2014 フォルダをフォールバック走査
for y in ["2014"]:
    ydir=RAW/y
    if not ydir.exists(): continue
    for fp in ydir.rglob("*.json"):
        m=re.search(r"(20\d{2})[\\/](\d{2})[\\/](\d{2})", str(fp))
        if not m: continue
        ymd = "-".join(m.groups())
        if not ("2014-01-01" <= ymd <= "2014-12-31"): continue
        try:
            j=json.loads(fp.read_text(encoding="utf-8"))
            t=str(j.get("ticker",""))
            if re.match(r"^\d{4}\.T$", t): tick.add(t)
        except: pass

pd.Series(sorted(tick)).to_csv(OUT, index=False, header=False)
print({"tickers_2014": len(tick), "out": str(OUT),
       "feat_date_min": str(pd.read_parquet(FEAT, columns=["date"])["date"].min().date()) if FEAT.exists() else None,
       "feat_date_max": str(pd.read_parquet(FEAT, columns=["date"])["date"].max().date()) if FEAT.exists() else None})
