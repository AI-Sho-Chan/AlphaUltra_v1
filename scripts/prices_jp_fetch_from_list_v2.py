# -*- coding: utf-8 -*-
import io, sys, time, requests as rq, pandas as pd, yfinance as yf
from pathlib import Path

LIST = Path("data/tmp/tickers_2014.csv")
RAW  = Path("data/raw/prices"); RAW.mkdir(parents=True, exist_ok=True)

def stooq(t):
    code=t.split(".")[0].lower(); url=f"https://stooq.com/q/d/l/?s={code}.jp&i=d"
    r=rq.get(url,timeout=15)
    try: df=pd.read_csv(io.StringIO(r.text))
    except: return None
    if df.shape[0]>=2 and {"Date","Close"}.issubset(df.columns):
        out=pd.DataFrame({"ticker":t,"date":pd.to_datetime(df["Date"]).dt.normalize(),
                          "adj_close":pd.to_numeric(df["Close"],errors="coerce"),
                          "volume":pd.to_numeric(df.get("Volume"),errors="coerce")}).dropna(subset=["date","adj_close"])
        return out if not out.empty else None
    return None

def yf_fetch(t):
    d=yf.download(t, start="2000-01-01", progress=False, auto_adjust=True, threads=False)
    if d is None or d.empty: return None
    d=d.reset_index()
    if "Date" not in d or "Close" not in d: return None
    out=pd.DataFrame({"ticker":t,"date":pd.to_datetime(d["Date"]).dt.normalize(),
                      "adj_close":pd.to_numeric(d["Close"],errors="coerce"),
                      "volume":pd.to_numeric(d.get("Volume"),errors="coerce")}).dropna(subset=["date","adj_close"])
    return out if not out.empty else None

tick=[l.strip() for l in LIST.read_text(encoding="utf-8").splitlines() if l.strip()]
have=set(p.name.split("_",1)[-1].split(".")[0] for p in RAW.glob("stooq_*.parquet"))|\
     set(p.name.split("_",1)[-1].split(".")[0] for p in RAW.glob("yf_*.parquet"))
todo=[t for t in tick if t.split(".")[0].lower() not in have]

ok=fail=0
for i,t in enumerate(todo,1):
    df=stooq(t)
    if df is None: df=yf_fetch(t)
    if df is not None:
        code=t.split(".")[0].lower()
        df.to_parquet(RAW/f"{'stooq' if 'Date' in df.columns else 'yf'}_{code}.parquet", index=False)
        ok+=1
    else:
        fail+=1
    if i%200==0: time.sleep(0.5)
print({"list": str(LIST), "todo": len(todo), "ok": ok, "fail": fail})
