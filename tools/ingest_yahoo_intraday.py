import argparse, pathlib, pandas as pd, sys, time
try:
    import yfinance as yf
except ImportError:
    print("[yh-intraday] yfinance not installed"); sys.exit(0)

ROOT = pathlib.Path(r"C:\AI\AlphaUltra")
BRONZE = ROOT/"data/bronze/yh_intraday"
GOLD   = ROOT/"data/gold/yh_intraday"

def load_tickers(args):
    ticks=[]
    if args.tickers:
        ticks += [t.strip() for t in args.tickers.split(",") if t.strip()]
    if args.tickers_file and pathlib.Path(args.tickers_file).exists():
        txt = pathlib.Path(args.tickers_file).read_text(encoding="utf-8", errors="ignore")
        if txt.startswith("\ufeff"): txt = txt.lstrip("\ufeff")
        for line in txt.splitlines():
            s=line.strip()
            if not s or s.startswith("#") or s.startswith(";"): continue
            if any(ord(ch)>127 for ch in s): continue
            ticks.append(s)
    return sorted({t for t in ticks if t})

def flatten_cols(df: pd.DataFrame):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ["_".join([str(x) for x in col if str(x)]) for col in df.columns]
    else:
        df.columns = [str(c) for c in df.columns]
    if "Datetime" in df.columns: df.rename(columns={"Datetime":"date"}, inplace=True)
    elif "Date" in df.columns:   df.rename(columns={"Date":"date"}, inplace=True)
    df.columns = [c.lower().replace(" ","_") for c in df.columns]
    return df

def to_numeric(df, cols):
    for c in cols:
        df[c] = pd.to_numeric(df.get(c), errors="coerce")
    return df

def fetch_one(t, lookback_days):
    try:
        df = yf.download(t, period=f"{lookback_days}d", interval="1m", auto_adjust=False, progress=False, threads=False)
        if df is None or df.empty:
            print(f"[yh-intraday] empty: {t}"); return None
        df = df.reset_index()
        df = flatten_cols(df)
        if "date" not in df.columns:
            print(f"[yh-intraday] missing date col: {t}"); return None
        df["ticker"] = t
        keep = ["date","ticker","open","high","low","close","volume","adj_close"]
        for k in ["open","high","low","close","volume","adj_close"]:
            if k not in df.columns: df[k]=pd.NA
        out = df[keep].copy()
        out["date"] = pd.to_datetime(out["date"], errors="coerce")
        out = out.dropna(subset=["date"])
        out = to_numeric(out, ["open","high","low","close","volume","adj_close"])
        return out
    except Exception as e:
        print(f"[yh-intraday] {t}: {e}")
        return None

def engineer(feat):
    feat = feat.sort_values(["ticker","date"]).copy()
    # returns（fill_method=Noneで将来非推奨回避）
    feat["ret1"] = feat.groupby("ticker")["close"].pct_change(1, fill_method=None)
    feat["ret5"] = feat.groupby("ticker")["close"].pct_change(5, fill_method=None)
    # volume z（numeric only）
    def vol_z(s):
        s = pd.to_numeric(s, errors="coerce").astype("float64")
        m = s.rolling(60, min_periods=10).mean()
        v = s.rolling(60, min_periods=10).std(ddof=0)
        return (s - m) / (v + 1e-9)
    feat["vol_z"] = feat.groupby("ticker")["volume"].transform(vol_z)
    # label（次バー）
    lab = feat[["date","ticker","close"]].copy()
    lab["fret1"] = lab.groupby("ticker")["close"].pct_change(-1, fill_method=None)
    lab = lab.drop(columns=["close"])
    return feat, lab

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", default="")
    ap.add_argument("--tickers-file", default=str(ROOT/"data/aux/watchlist.txt"))
    ap.add_argument("--lookback_days", type=int, default=2)
    args = ap.parse_args()

    tickers = load_tickers(args)
    if not tickers:
        print("[yh-intraday] no tickers"); return

    parts=[]
    for t in tickers:
        d = fetch_one(t, args.lookback_days)
        if d is not None: parts.append(d)
        time.sleep(0.2)

    if not parts:
        print("[yh-intraday] no data fetched"); return

    raw = pd.concat(parts, ignore_index=True).drop_duplicates(subset=["ticker","date"])
    BRONZE.mkdir(parents=True, exist_ok=True)
    (BRONZE/"ohlcv.parquet").write_bytes(raw.to_parquet(index=False))
    print(f"[bronze] {BRONZE/'ohlcv.parquet'} rows={len(raw):,}")

    feat, lab = engineer(raw)
    GOLD.mkdir(parents=True, exist_ok=True)
    feat.to_parquet(GOLD/"features.parquet", index=False)
    lab.to_parquet(GOLD/"labels.parquet", index=False)
    print(f"[gold] features={GOLD/'features.parquet'} labels={GOLD/'labels.parquet'}")

if __name__ == "__main__":
    main()
