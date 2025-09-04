# -*- coding: utf-8 -*-
import io, requests as rq, pandas as pd
from pathlib import Path

IN  = Path("data/tmp/tickers_A.csv")
RAW = Path("data/raw/prices"); RAW.mkdir(parents=True, exist_ok=True)

tick = [l.strip() for l in IN.read_text(encoding="utf-8").splitlines() if l.strip()]
ok = fail = 0
for t in tick:
    code = t.split(".")[0].lower()
    url  = f"https://stooq.com/q/d/l/?s={code}.jp&i=d"
    try:
        r = rq.get(url, timeout=15)
        df = pd.read_csv(io.StringIO(r.text))
        if df.shape[0] >= 2 and {"Date","Close"}.issubset(df.columns):
            out = pd.DataFrame({
                "ticker": t,
                "date": pd.to_datetime(df["Date"]).dt.normalize(),
                "adj_close": pd.to_numeric(df["Close"], errors="coerce"),
                "volume": pd.to_numeric(df.get("Volume"), errors="coerce")
            }).dropna(subset=["date","adj_close"])
            if not out.empty:
                out.to_parquet(RAW / f"stooq_{code}.parquet", index=False)
                ok += 1
                continue
    except Exception:
        pass
    fail += 1

print({"ok": ok, "fail": fail, "raw_dir": str(RAW)})
