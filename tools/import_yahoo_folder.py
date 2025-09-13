#!/usr/bin/env python
"""
Import a folder of Yahoo-style OHLCV CSVs, normalize to Parquet, and build
minimal features/labels. Finally updates data/datasets_registry.yaml.

Expected CSV columns per file (typical Yahoo Finance export):
  Date, Open, High, Low, Close, Adj Close, Volume

Ticker resolution order:
  - Use column in ['ticker','symbol','code'] if present
  - Else fallback to file stem as ticker

Outputs (defaults):
  - data/gold/features_eng.parquet
  - data/gold/labels_eng.parquet

Usage:
  python tools/import_yahoo_folder.py --input-folder C:\path\to\csvs
"""
import argparse
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
GOLD_DIR = DATA_DIR / "gold"
BRONZE_DIR = DATA_DIR / "bronze"
REGISTRY_PATH = DATA_DIR / "datasets_registry.yaml"


def _ensure_dirs():
    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    BRONZE_DIR.mkdir(parents=True, exist_ok=True)


def _read_csv_guess_ticker(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    cols = {c.lower(): c for c in df.columns}
    # Normalize column names used below
    date_col = cols.get("date") or cols.get("timestamp") or cols.get("time")
    if not date_col:
        raise ValueError(f"No date-like column found in {path.name}")
    df.rename(columns={date_col: "date"}, inplace=True)
    for cand in ["open", "high", "low", "close", "adj close", "adj_close", "adjclose", "volume", "vol"]:
        if cand in cols:
            df.rename(columns={cols[cand]: cand.replace(" ", "_")}, inplace=True)
    # Ticker resolution
    ticker = None
    for k in ("ticker", "symbol", "code"):
        if k in cols:
            ticker = str(df.iloc[0][cols[k]]) if not pd.isna(df.iloc[0][cols[k]]) else None
            break
    if not ticker:
        ticker = path.stem
    df["ticker"] = str(ticker)
    # Parse date
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
    # Select canonical columns if present
    keep = [c for c in ["date", "ticker", "open", "high", "low", "close", "adj_close", "volume", "vol"] if c in df.columns]
    df = df[keep].copy()
    if "volume" not in df.columns and "vol" in df.columns:
        df.rename(columns={"vol": "volume"}, inplace=True)
    df.sort_values(["ticker", "date"], inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def normalize_folder(input_folder: Path) -> pd.DataFrame:
    csvs = sorted([p for p in input_folder.glob("**/*.csv") if p.is_file()])
    if not csvs:
        raise SystemExit(f"No CSV files found under {input_folder}")
    frames = []
    for p in csvs:
        try:
            frames.append(_read_csv_guess_ticker(p))
        except Exception as e:
            print(f"[warn] skip {p.name}: {e}")
    if not frames:
        raise SystemExit("No usable CSVs")
    df = pd.concat(frames, ignore_index=True)
    # Persist a bronze parquet for traceability
    bronze_path = BRONZE_DIR / f"yahoo_ohlcv_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet"
    try:
        df.to_parquet(bronze_path, index=False)
        print(f"[bronze] {bronze_path}")
    except Exception as e:
        print(f"[warn] parquet write failed ({e}); continuing without bronze snapshot")
    return df


def build_features_labels(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    df = df.copy()
    # Close available? If not, try adj_close
    if "close" not in df.columns and "adj_close" in df.columns:
        df["close"] = df["adj_close"]
    # Basic returns per ticker
    df["ret_1d"] = df.sort_values(["ticker", "date"]).groupby("ticker")["close"].pct_change()
    df["ma_5"] = df.groupby("ticker")["close"].transform(lambda s: s.rolling(5, min_periods=3).mean())
    df["ma_20"] = df.groupby("ticker")["close"].transform(lambda s: s.rolling(20, min_periods=5).mean())
    df["vol_20"] = df.groupby("ticker")["ret_1d"].transform(lambda s: s.rolling(20, min_periods=5).std())

    def z(x: pd.Series):
        s = x.std(ddof=1)
        return (x - x.mean()) / s if s and s != 0 else 0

    df["z_ret_1d"] = df.groupby("ticker")["ret_1d"].transform(z)

    features = df[["date", "ticker", "close", "ret_1d", "ma_5", "ma_20", "vol_20", "z_ret_1d"]].dropna().copy()

    # Labels: forward returns
    df["fwd_close_5"] = df.groupby("ticker")["close"].shift(-5)
    df["fwd_close_20"] = df.groupby("ticker")["close"].shift(-20)
    labels = df[["date", "ticker", "close", "fwd_close_5", "fwd_close_20"]].copy()
    labels["fwd_ret_5d"] = (labels["fwd_close_5"] / labels["close"]) - 1.0
    labels["fwd_ret_20d"] = (labels["fwd_close_20"] / labels["close"]) - 1.0
    labels["target_up_5d"] = (labels["fwd_ret_5d"] > 0).astype(int)
    labels = labels.drop(columns=["fwd_close_5", "fwd_close_20", "close"]).dropna().copy()
    return features, labels


def _split_front_matter(yaml_text: str) -> Tuple[str, str]:
    # Return (fm, body) where fm includes --- block or '' if none
    if not yaml_text.startswith("---"):
        return "", yaml_text
    parts = yaml_text.split("\n---\n", 1)
    if len(parts) == 2:
        return parts[0] + "\n---\n", parts[1]
    return "", yaml_text


def update_registry(dataset_name: str, features_path: Path, labels_path: Path) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    fm = ""
    body = ""
    if REGISTRY_PATH.exists():
        txt = REGISTRY_PATH.read_text(encoding="utf-8")
        fm, body = _split_front_matter(txt)
        try:
            data = pd.io.json._json.loads(body)  # unlikely to be JSON
        except Exception:
            import yaml as _yaml
            data = _yaml.safe_load(body) if body.strip() else {}
    else:
        data = {}
    if not isinstance(data, dict):
        data = {}
    datasets = data.get("datasets", {})
    datasets[dataset_name] = {
        "features_path": str(features_path.resolve()),
        "labels_path": str(labels_path.resolve()),
        "calendar": "JPX_TSE",
        "tz": "Asia/Tokyo",
        "universe": "CUSTOM",
        "note": "yahoo engineered features",
    }
    data["datasets"] = datasets
    import yaml
    new_body = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
    REGISTRY_PATH.write_text((fm if fm else "---\nalphaultra:\n  type: data\n  topic: eval\n  task: analysis\n  target_dir: data\n  date: %s\n---\n" % datetime.now().date()) + new_body, encoding="utf-8")
    print(f"[registry] updated {REGISTRY_PATH} with dataset '{dataset_name}'")


def main(argv=None):
    p = argparse.ArgumentParser(description="Import Yahoo OHLCV CSV folder -> Parquet + features/labels")
    p.add_argument("--input-folder", required=True, help="Folder containing Yahoo CSV files")
    p.add_argument("--dataset-name", default="yahoo_default", help="Registry dataset key to write/update")
    p.add_argument("--out-features", default=str(GOLD_DIR / "features_eng.parquet"), help="Output features parquet path")
    p.add_argument("--out-labels", default=str(GOLD_DIR / "labels_eng.parquet"), help="Output labels parquet path")
    args = p.parse_args(argv)

    _ensure_dirs()
    in_dir = Path(args.input_folder)
    if not in_dir.exists():
        raise SystemExit(f"Input folder not found: {in_dir}")

    df = normalize_folder(in_dir)
    f, y = build_features_labels(df)

    fpath = Path(args.out_features)
    lpath = Path(args.out_labels)
    try:
        f.to_parquet(fpath, index=False)
        y.to_parquet(lpath, index=False)
    except Exception as e:
        print(f"[error] writing parquet failed: {e}")
        raise
    print(f"[gold] features -> {fpath}")
    print(f"[gold] labels   -> {lpath}")

    update_registry(args.dataset_name, fpath, lpath)
    print("[done] Yahoo import + features/labels complete")


if __name__ == "__main__":
    main()

