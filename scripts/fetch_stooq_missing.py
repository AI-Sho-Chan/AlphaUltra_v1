import os, io, sys, json, time, pandas as pd, requests as rq
from pathlib import Path

FEAT = Path("data/proc/features_tdnet/tdnet_event_features.parquet")
PXSTD= Path("data/proc/prices/jp_prices_std.parquet")
RAW  = Path("data/raw/prices"); RAW.mkdir(parents=True, exist_ok=True)

df = pd.read_parquet(FEAT)[["ticker"]].drop_duplicates()
feat_tickers = set(df["ticker"].astype(str))
px_tickers = set()
if PXSTD.exists():
    px_tickers = set(pd.read_parquet(PXSTD)["ticker"].astype(str))

missing = sorted(t for t in feat_tickers if t.endswith(".T") and t not in px_tickers)
ok=0; fail=[]
for t in missing:
    code = t.split(".")[0].lower()
    url = f"https://stooq.com/q/d/l/?s={code}.jp&i=d"
    try:
        resp = rq.get(url, timeout=15)
        if resp.status_code!=200 or len(resp.text.splitlines())<2:
            fail.append((t,"http"))
            continue
        d = pd.read_csv(io.StringIO(resp.text))
        # 期待列: Date, Open, High, Low, Close, Volume
        if "Date" not in d or "Close" not in d:
            fail.append((t,"cols"))
            continue
        out = pd.DataFrame({
            "date": pd.to_datetime(d["Date"]).dt.normalize(),
            "ticker": t,
            "adj_close": pd.to_numeric(d["Close"], errors="coerce"),
            "volume": pd.to_numeric(d.get("Volume"), errors="coerce")
        }).dropna(subset=["date","adj_close"])
        if out.empty:
            fail.append((t,"empty"))
            continue
        out.to_parquet(RAW/f"stooq_{code}.parquet", index=False)
        ok+=1
        time.sleep(0.4)
    except Exception as e:
        fail.append((t,"exc"))

print(json.dumps({"tried": len(missing), "ok": ok, "fail": len(fail)}, ensure_ascii=False))
