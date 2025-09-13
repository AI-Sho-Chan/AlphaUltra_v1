# -*- coding: utf-8 -*-
import re, json
from pathlib import Path
import pandas as pd

FEAT = Path("data/proc/features_tdnet/tdnet_event_features.parquet")
RAW  = Path("data/raw/tdnet")
OUT  = Path("data/tmp/tickers_2014.csv"); OUT.parent.mkdir(parents=True, exist_ok=True)

tick=set()
def norm_code4_from_any(s):
    if not isinstance(s,str): return None
    m=re.search(r'(?<!\d)(\d{4})(?!\d)', s)
    return m.group(1) if m else None

# 1) features から 2014 年だけ抽出（ticker/コード表記の揺れを許容）
if FEAT.exists():
    d=pd.read_parquet(FEAT, columns=["ticker","date"])
    d["date"]=pd.to_datetime(d["date"], errors="coerce")
    win=d[(d["date"]>= "2014-01-01") & (d["date"]<= "2014-12-31")].dropna(subset=["date"])
    for s in win["ticker"].astype(str).unique():
        c4 = norm_code4_from_any(s)
        if c4: tick.add(f"{c4}.T")

# 2) raw/tdnet から 2014 年をフォールバック抽出（code4→ticker生成）
if RAW.exists():
    for fp in RAW.rglob("*.json"):
        m=re.search(r"(20\d{2})[\\/](\d{2})[\\/](\d{2})", str(fp))
        if not m: continue
        ymd="-".join(m.groups())
        if not ("2014-01-01" <= ymd <= "2014-12-31"): continue
        try:
            j=json.loads(fp.read_text(encoding="utf-8"))
        except: 
            continue
        c4 = str(j.get("code4") or "") or norm_code4_from_any(str(j.get("ticker") or ""))
        if c4 and re.fullmatch(r"\d{4}", c4):
            tick.add(f"{c4}.T")

pd.Series(sorted(tick)).to_csv(OUT, index=False, header=False)
print({"tickers_2014": len(tick), "out": str(OUT)})
