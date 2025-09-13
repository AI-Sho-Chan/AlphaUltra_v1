import yfinance as yf
import pandas as pd
import pandas_datareader.data as pdr
import yaml, time, requests
from pathlib import Path
from utils.io_utils import ensure_dir, write_parquet, now_utc_str
from utils.log_utils import get_logger

logger = get_logger()

def fetch_yahoo(ticker: str, start: str, end: str, session: requests.Session):
    tk = yf.Ticker(ticker, session=session)
    hist = tk.history(start=start, end=end, interval="1d", auto_adjust=False, actions=True)
    if hist is None or hist.empty:
        return None, None
    px = hist[["Open","High","Low","Close","Adj Close","Volume"]].rename(
        columns={"Open":"open","High":"high","Low":"low","Close":"close","Adj Close":"adj_close","Volume":"volume"}
    ).reset_index().rename(columns={"Date":"date"})
    px["security_id"] = ticker
    px["asof_ts"] = now_utc_str()

    acts = pd.DataFrame(index=hist.index)
    if "Dividends" in hist.columns:
        acts["dividend"] = hist["Dividends"]
    if "Stock Splits" in hist.columns:
        acts["split_ratio"] = hist["Stock Splits"]
    acts = acts.reset_index().rename(columns={"Date":"date"})
    acts["security_id"] = ticker
    acts["asof_ts"] = now_utc_str()
    acts = acts[(acts.get("dividend",0).fillna(0)!=0) | (acts.get("split_ratio",0).fillna(0)!=0)]
    return px, acts

def fetch_stooq(ticker: str, start: str, end: str):
    # Map some common symbols to Stooq equivalents
    mapping = {
        "^GSPC": "^SPX",  # stooq uses ^spx for index price series; but we default to SPY benchmark
        "SPY": "SPY.US",
        "AAPL": "AAPL.US",
        "MSFT": "MSFT.US",
        "7203.T": "7203.JP",
        "9984.T": "9984.JP",
    }
    sym = mapping.get(ticker, ticker)
    try:
        df = pdr.DataReader(sym, "stooq", start=start, end=end)
    except Exception as e:
        logger.warning(f"stooq fail {ticker}: {e}")
        return None, None
    if df is None or df.empty:
        return None, None
    df = df.sort_index()
    px = df[["Open","High","Low","Close","Volume"]].rename(columns=str.lower).reset_index().rename(columns={"Date":"date"})
    px["adj_close"] = px["close"]  # stooq has no separate adj close; treat equal
    px["security_id"] = ticker
    px["asof_ts"] = now_utc_str()
    acts = pd.DataFrame(columns=["date","security_id","dividend","split_ratio","asof_ts"])
    return px, acts

def main(cfg_path: str):
    cfg = yaml.safe_load(Path(cfg_path).read_text(encoding="utf-8"))
    start, end = cfg["start"], cfg["end"]
    uni = cfg["universe"]["us"] + cfg["universe"]["jp"]
    spx = cfg["benchmark"]["spx"]
    fx_pairs = cfg.get("fx",{}).get("pairs",[])

    raw_dir = Path(cfg["paths"]["raw"])
    px_dir = ensure_dir(raw_dir / "prices")
    ac_dir = ensure_dir(raw_dir / "actions")
    idx_dir = ensure_dir(raw_dir / "index")
    fx_dir = ensure_dir(raw_dir / "fx")

    tickers = list(dict.fromkeys(uni + [spx] + fx_pairs))

    sess = requests.Session()
    # minimal headers to avoid anti-bot false positives
    sess.headers.update({"User-Agent": "Mozilla/5.0", "Accept": "application/json,text/*,*/*;q=0.8"})

    for t in tickers:
        logger.info(f"fetch {t}")
        px, acts = fetch_yahoo(t, start, end, sess)
        if px is None or px.empty:
            logger.warning(f"yahoo empty: {t} -> try stooq")
            px, acts = fetch_stooq(t, start, end)
        if px is None or px.empty:
            logger.warning(f"no data: {t}")
            continue
        write_parquet(px, px_dir / f"{t}.parquet")
        if acts is not None and not acts.empty:
            write_parquet(acts, ac_dir / f"{t}.parquet")
        time.sleep(0.3)  # polite

    logger.info("ingest done.")

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/base.yaml")
    args = ap.parse_args()
    main(args.config)
