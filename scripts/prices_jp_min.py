from pathlib import Path
import pandas as pd, time

events_path = Path(r"C:\AI\AlphaUltra_v1\data\proc\features_tdnet\tdnet_event_features.parquet")
out_path    = Path(r"C:\AI\AlphaUltra_v1\data\proc\prices\jp_prices.parquet")
out_path.parent.mkdir(parents=True, exist_ok=True)
start = "2018-01-01"

tickers = []
if events_path.exists():
    ev = pd.read_parquet(events_path)
    tickers = sorted(ev["ticker"].dropna().unique().tolist())
print({"tickers": len(tickers)})

def try_import_yf():
    try:
        import yfinance as yf
        return yf
    except Exception:
        return None

def fetch_yf(yf, ticker, start):
    try:
        d = yf.download(ticker, start=start, progress=False, auto_adjust=True, threads=False)
        if d is None or d.empty:
            return pd.DataFrame(columns=["date","adj_close"])
        d = d.reset_index()
        d["Date"] = pd.to_datetime(d["Date"], errors="coerce")
        d = d.dropna(subset=["Date"])
        d = d.rename(columns={"Date":"date","Close":"adj_close"})
        return d[["date","adj_close"]].sort_values("date")
    except Exception:
        return pd.DataFrame(columns=["date","adj_close"])

def fetch_stooq(ticker, start):
    try:
        sym = ticker.lower().replace(".t",".jp")
        url = f"https://stooq.com/q/d/l/?s={sym}&i=d"
        df = pd.read_csv(url)
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Date"])
        df = df[df["Date"] >= pd.to_datetime(start)]
        df = df.rename(columns={"Date":"date","Close":"adj_close"})
        return df[["date","adj_close"]].sort_values("date")
    except Exception:
        return pd.DataFrame(columns=["date","adj_close"])

yf = try_import_yf()
rows=[]
for i,t in enumerate(tickers,1):
    df = fetch_yf(yf, t, start) if yf else pd.DataFrame()
    if df.empty:
        df = fetch_stooq(t, start)
    if not df.empty:
        df.insert(0,"ticker",t)
        rows.append(df)
    print(f"{i}/{len(tickers)} {t} rows={len(df)}")
    time.sleep(0.2)

out = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["ticker","date","adj_close"])
out = out.sort_values(["ticker","date"])
out.to_parquet(out_path, index=False)
print({"out": out_path.as_posix(), "rows": int(len(out)), 
       "date_min": None if out.empty else str(pd.to_datetime(out['date']).min().date()),
       "date_max": None if out.empty else str(pd.to_datetime(out['date']).max().date())})
