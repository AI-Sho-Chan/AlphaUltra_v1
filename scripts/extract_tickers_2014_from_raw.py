# -*- coding: utf-8 -*-
import re, json
from pathlib import Path
import pandas as pd

RAW = Path("data/raw/tdnet")
OUT = Path("data/tmp/tickers_2014.csv"); OUT.parent.mkdir(parents=True, exist_ok=True)

tick=set()
for fp in RAW.rglob("*.json"):
    m=re.search(r"(20\d{2})[\\/](\d{2})[\\/](\d{2})", str(fp))
    if not m: 
        continue
    ymd="-".join(m.groups())
    if not ("2014-01-01" <= ymd <= "2014-12-31"):
        continue
    try:
        j=json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        continue
    # 優先：code4 → 補助：tickerから4桁抽出
    code4 = str(j.get("code4") or "")
    if not re.fullmatch(r"\d{4}", code4):
        t = str(j.get("ticker") or "")
        m4 = re.search(r"(?<!\d)(\d{4})(?!\d)", t)
        code4 = m4.group(1) if m4 else ""
    if re.fullmatch(r"\d{4}", code4):
        tick.add(f"{code4}.T")

pd.Series(sorted(tick)).to_csv(OUT, index=False, header=False)
print({"tickers_2014": len(tick), "out": str(OUT)})
