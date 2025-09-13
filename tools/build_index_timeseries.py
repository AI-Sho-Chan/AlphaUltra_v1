# -*- coding: utf-8 -*-
import argparse, sys
from pathlib import Path
import pandas as pd
import yaml

TICKER_MAP = {
    "^N225": "nikkei",
    "^GSPC": "spx",
    "USDJPY=X": "usdjpy",
    "GC=F": "gold",
    "^VIX": "vix",
}

def load_registry(p):
    y = yaml.safe_load(Path(p).read_text(encoding="utf-8")) or {}
    return y

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", default="data/datasets_registry.yaml")
    ap.add_argument("--dataset-key", default="yahoo_default")
    ap.add_argument("--out", default="data/aux/index_timeseries.csv")
    args = ap.parse_args()

    reg = load_registry(args.registry)
    ds = reg.get("datasets", {}).get(args.dataset_key)
    if not ds:
        print(f"[ERR] dataset_key not found: {args.dataset_key}", file=sys.stderr)
        sys.exit(1)

    fpath = Path(ds["features_path"])
    if not fpath.exists():
        print(f"[ERR] features parquet missing: {fpath}", file=sys.stderr)
        sys.exit(1)

    df = pd.read_parquet(fpath)[["date","ticker","close"]].copy()
    df["date"] = pd.to_datetime(df["date"])
    df["ticker"] = df["ticker"].astype(str)

    keep = df[df["ticker"].isin(TICKER_MAP.keys())]
    if keep.empty:
        print("[WARN] no index/macro tickers found in features; writing empty skeleton CSV")
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame({"date":[], "close":[], "nikkei":[], "spx":[], "usdjpy":[], "gold":[], "vix":[]}).to_csv(args.out, index=False)
        print(f"[index_ts] {args.out} (empty)")
        return

    pivot = keep.pivot_table(index="date", columns="ticker", values="close", aggfunc="last").sort_index()
    wide = pivot.rename(columns=TICKER_MAP).reset_index().rename(columns={"index":"date"})
    cols = ["date","nikkei","spx","usdjpy","gold","vix"]
    for c in cols:
        if c not in wide.columns: wide[c] = pd.NA

    # make a generic 'close' for downstream scripts (prefer nikkei -> spx)
    wide["close"] = wide["nikkei"].fillna(wide["spx"])
    # 最低限: date, close があれば make_regimes.py の既定ロジックで動く想定
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    wide.to_csv(args.out, index=False)
    print(f"[index_ts] wrote: {args.out} rows={len(wide)}")

if __name__ == "__main__":
    main()
