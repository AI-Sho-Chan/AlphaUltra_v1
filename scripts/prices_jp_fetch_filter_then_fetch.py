#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import io
import sys
import time
from pathlib import Path
import requests as rq
import pandas as pd
import yfinance as yf


RAW = Path("data/raw/prices")
RAW.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "alphaai-price-fetcher/1.0"}


def stooq_probe_and_fetch(t: str) -> pd.DataFrame | None:
    code = t.split(".")[0].lower()
    url = f"https://stooq.com/q/d/l/?s={code}.jp&i=d"
    try:
        r = rq.get(url, timeout=20, headers=UA)
    except Exception:
        return None
    if r.status_code != 200:
        return None
    # try parse CSV
    try:
        df = pd.read_csv(io.StringIO(r.text))
    except Exception:
        return None
    if df.shape[0] >= 2 and {"Date", "Close"}.issubset(df.columns):
        out = pd.DataFrame({
            "ticker": t,
            "date": pd.to_datetime(df["Date"], errors="coerce").dt.normalize(),
            "adj_close": pd.to_numeric(df["Close"], errors="coerce"),
            "volume": pd.to_numeric(df.get("Volume"), errors="coerce"),
        }).dropna(subset=["date", "adj_close"]).reset_index(drop=True)
        return out if not out.empty else None
    return None


def yf_fetch(t: str) -> pd.DataFrame | None:
    try:
        d = yf.download(t, start="1999-01-01", progress=False, auto_adjust=True, threads=False)
    except Exception:
        return None
    if d is None or d.empty:
        return None
    d = d.reset_index()
    if "Date" not in d or "Close" not in d:
        return None
    out = pd.DataFrame({
        "ticker": t,
        "date": pd.to_datetime(d["Date"], errors="coerce").dt.normalize(),
        "adj_close": pd.to_numeric(d["Close"], errors="coerce"),
        "volume": pd.to_numeric(d.get("Volume"), errors="coerce"),
    }).dropna(subset=["date", "adj_close"]).reset_index(drop=True)
    return out if not out.empty else None


def main():
    if len(sys.argv) < 2:
        print("usage: prices_jp_fetch_filter_then_fetch.py DATA/TMP/TICKERS.csv")
        sys.exit(2)
    in_csv = Path(sys.argv[1])
    tick = [l.strip() for l in in_csv.read_text(encoding="utf-8").splitlines() if l.strip()]

    # skip cache
    have = set(p.name.split("_", 1)[-1].split(".")[0] for p in RAW.glob("stooq_*.parquet")) | \
           set(p.name.split("_", 1)[-1].split(".")[0] for p in RAW.glob("yf_*.parquet"))
    todo = [t for t in tick if t.split(".")[0].lower() not in have]

    ok = fail = 0
    for i, t in enumerate(todo, 1):
        code = t.split(".")[0].lower()
        df = stooq_probe_and_fetch(t)
        if df is not None:
            df.to_parquet(RAW / f"stooq_{code}.parquet", index=False)
            ok += 1
        else:
            df = yf_fetch(t)
            if df is not None:
                df.to_parquet(RAW / f"yf_{code}.parquet", index=False)
                ok += 1
            else:
                fail += 1
        if i % 200 == 0:
            time.sleep(0.5)
    print({"list": str(in_csv), "todo": len(todo), "ok": ok, "fail": fail})


if __name__ == "__main__":
    main()

