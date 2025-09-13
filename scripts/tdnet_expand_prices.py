import argparse, re, time, yaml
from pathlib import Path
import pandas as pd
import yfinance as yf
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from pandas_datareader.stooq import StooqDailyReader

ETF_PAT = re.compile(r"^\s*(13|15|16)\d{2}\.T\s*$")  # JP ETF系

def is_etf(t): return ETF_PAT.match((t or "").upper()) is not None
def stooq_symbol(t): return t.strip().upper().replace(".T", ".JP")

@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=0.6, min=0.6, max=4),
       retry=retry_if_exception_type(Exception))
def dl_stooq(t, start):
    rdr = StooqDailyReader(symbols=stooq_symbol(t), start=pd.to_datetime(start))
    d = rdr.read()
    if d is None or d.empty: raise RuntimeError("stooq empty")
    if isinstance(d.columns, pd.MultiIndex): d = d.droplevel(0, axis=1)
    d.index = pd.to_datetime(d.index).tz_localize(None)
    return d[["Close","Volume"]].rename(columns={"Close":"adj_close","Volume":"volume"}).reset_index(names="date")

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.8, min=0.8, max=6),
       retry=retry_if_exception_type(Exception))
def dl_yf(t, start):
    d = yf.download(t.strip().upper(), start=start, auto_adjust=True, progress=False, threads=False)
    if d is None or d.empty: raise RuntimeError("yf empty")
    d.index = pd.to_datetime(d.index).tz_localize(None)
    return d[["Close","Volume"]].rename(columns={"Close":"adj_close","Volume":"volume"}).reset_index(names="date")

def fetch_one(t, start):
    if is_etf(t): return None, "skip_etf"
    try:
        return dl_stooq(t, start), "stooq"
    except Exception as e1:
        try:
            return dl_yf(t, start), "yf"
        except Exception as e2:
            return None, f"fail:{e1}|{e2}"

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--config", default="configs/tdnet_model.yaml")
    args=ap.parse_args()
    cfg=yaml.safe_load(open(args.config,"r",encoding="utf-8"))
    tdnet_path = Path(cfg["paths"]["tdnet_features"])
    adj_root   = Path(cfg["paths"]["adj_root"]); adj_root.mkdir(parents=True, exist_ok=True)
    start      = cfg["expand_prices"]["lookback_start"]
    top_n      = int(cfg["expand_prices"].get("top_n_jp", 80))
    blocklist  = set(map(str.upper, cfg["expand_prices"].get("blocklist", [])))

    td = pd.read_parquet(tdnet_path)
    td["ticker"] = td["ticker"].astype(str).str.strip().str.upper()
    jp = td[td["ticker"].str.endswith(".T")]
    top = [t for t in jp["ticker"].value_counts().index.tolist() if t not in blocklist and not is_etf(t)]
    top = top[:top_n]

    need = [t for t in top if not (adj_root/f"{t}.parquet").exists()]
    print(f"[INFO] fetch JP tickers need={len(need)} / total_top={len(top)}")

    ok=0; src_ct={"yf":0,"stooq":0,"skip_etf":0,"fail":0}
    for i,t in enumerate(need,1):
        df, src = fetch_one(t, start)
        if df is not None and not df.empty:
            df.to_parquet(adj_root/f"{t}.parquet", index=False)
            ok+=1; src_ct[src]=src_ct.get(src,0)+1
        else:
            key="fail" if not (src or "").startswith("skip") else "skip_etf"
            src_ct[key]=src_ct.get(key,0)+1
        if i%20==0: print(f"[INFO] fetched {i}/{len(need)} so far")
        time.sleep(0.5)
    print(f"[INFO] done ok={ok} by {src_ct}")
if __name__=="__main__": main()
