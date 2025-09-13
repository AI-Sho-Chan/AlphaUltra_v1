
import os, math, yaml, numpy as np, pandas as pd
from pathlib import Path
from typing import Tuple

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def _detect_price_cols(df: pd.DataFrame):
    for c in ["adj_close","Adj Close","adjusted_close","close","Close"]:
        if c in df.columns: return c
    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if num_cols: return num_cols[0]
    raise ValueError("no numeric price column found")

def _detect_date_index(df: pd.DataFrame):
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], utc=True, errors="coerce").dt.tz_convert("UTC").dt.floor("D")
        return df.set_index("date").sort_index()
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], utc=True, errors="coerce").dt.tz_convert("UTC").dt.floor("D")
        df = df.rename(columns={"Date":"date"})
        return df.set_index("date").sort_index()
    if isinstance(df.index, pd.DatetimeIndex):
        df = df.copy()
        df.index = pd.to_datetime(df.index, utc=True, errors="coerce").tz_convert("UTC").floor("D")
        return df.sort_index()
    for c in df.columns:
        if "date" in c.lower():
            df[c] = pd.to_datetime(df[c], utc=True, errors="coerce").dt.tz_convert("UTC").dt.floor("D")
            df = df.rename(columns={c:"date"})
            return df.set_index("date").sort_index()
    raise ValueError("no date column/index found")

def _forward_max_ratio(p: np.ndarray, horizon: int) -> Tuple[np.ndarray, np.ndarray]:
    n = len(p)
    ratio = np.full(n, np.nan, dtype=float)
    ttd   = np.full(n, np.nan, dtype=float)
    for t in range(n):
        i1 = t+1
        i2 = min(n, t+1+horizon)
        if i1 >= n: break
        window = p[i1:i2]
        if window.size == 0: 
            continue
        mx = window.max()
        ratio[t] = mx / p[t] if p[t] > 0 else np.nan
        idx = window.argmax()
        ttd[t] = (idx + 1)
    return ratio, ttd

def _min_drawdown_forward(p: np.ndarray, horizon: int) -> np.ndarray:
    n = len(p)
    out = np.full(n, np.nan, dtype=float)
    for t in range(n):
        i1 = t+1; i2 = min(n, t+1+horizon)
        if i1 >= n: break
        w = p[i1:i2]
        if w.size == 0: continue
        dd = (w / p[t]) - 1.0
        out[t] = dd.min()
    return out

def _rel_return(p_stock: pd.Series, p_bench: pd.Series, n: int) -> pd.Series:
    s = p_stock
    b = p_bench.reindex_like(s).ffill()
    rs = (s.shift(-n) / s) - 1.0
    rb = (b.shift(-n) / b) - 1.0
    return rs - rb

def make_labels_for_file(f: Path, bench: pd.Series, cfg: dict) -> pd.DataFrame:
    try:
        df = pd.read_parquet(f)
    except Exception:
        return pd.DataFrame()
    try:
        df = _detect_date_index(df)
        col = _detect_price_cols(df)
    except Exception:
        return pd.DataFrame()
    s = df[col].astype(float).replace([np.inf,-np.inf], np.nan).dropna()
    idx = s.index.union(bench.index).unique().sort_values()
    s = s.reindex(idx).ffill()
    b = bench.reindex(idx).ffill()

    min_hist = int(cfg["options"].get("min_history_days", 300))
    if s.dropna().shape[0] < min_hist:
        return pd.DataFrame()

    h2 = int(cfg["targets"]["two_x_days"])
    h10 = int(cfg["targets"]["ten_x_days"])
    r1m = int(cfg["relative_windows"]["1M"]); r3m = int(cfg["relative_windows"]["3M"]); r12m = int(cfg["relative_windows"]["12M"])

    p = s.values.astype(float)
    ratio2, ttd2 = _forward_max_ratio(p, h2)
    ratio10, ttd10 = _forward_max_ratio(p, h10)
    dd_min = _min_drawdown_forward(p, h2) if bool(cfg["options"].get("save_drawdown", True)) else np.full_like(ratio2, np.nan)

    rel1 = _rel_return(s, b, r1m)
    rel3 = _rel_return(s, b, r3m)
    rel12= _rel_return(s, b, r12m)

    out = pd.DataFrame(index=s.index)
    out["ticker"] = f.stem
    out["y_2x"] = (ratio2 >= 2.0).astype(int)
    out["y_10x"] = (ratio10 >= 10.0).astype(int)
    if bool(cfg["options"].get("save_ttd", True)):
        out["ttd_2x"] = ttd2
        out["ttd_10x"] = ttd10
    if bool(cfg["options"].get("save_drawdown", True)):
        out["dd_min_252"] = dd_min

    out["rel_1M"] = rel1.values
    out["rel_3M"] = rel3.values
    out["rel_12M"] = rel12.values

    th = cfg.get("thresholds", {})
    out["hit_rel_1M_10p"]  = (out["rel_1M"]  >= float(th.get("rel_1M_hit", 0.10))).astype(int)
    out["hit_rel_3M_20p"]  = (out["rel_3M"]  >= float(th.get("rel_3M_hit", 0.20))).astype(int)
    out["hit_rel_12M_50p"] = (out["rel_12M"] >= float(th.get("rel_12M_hit",0.50))).astype(int)

    out = out.dropna(how="all")
    out = out.reset_index().rename(columns={"index":"date"})
    return out

def main(cfg_path: str):
    cfg = yaml.safe_load(Path(cfg_path).read_text(encoding="utf-8"))
    adj_dir = Path(cfg["paths"]["adj_prices_dir"])
    lbl_dir = Path(cfg["paths"]["labels_dir"])
    rep_dir = Path(cfg["paths"]["reports_dir"])
    bench_sym = cfg["benchmark"]["symbol"]
    ensure_dir(lbl_dir); ensure_dir(rep_dir)

    bench_file = adj_dir / f"{bench_sym}.parquet"
    if not bench_file.exists():
        alt = adj_dir / "^GSPC.parquet"
        if alt.exists():
            bench_file = alt
        else:
            raise SystemExit(f"benchmark parquet not found: {bench_file} or {alt}")

    bdf = pd.read_parquet(bench_file)
    bdf = _detect_date_index(bdf)
    bcol = _detect_price_cols(bdf)
    b = bdf[bcol].astype(float)

    rows = []
    for f in adj_dir.glob("*.parquet"):
        if f.name == bench_file.name:
            continue
        r = make_labels_for_file(f, b, cfg)
        if not r.empty:
            rows.append(r)

    if not rows:
        empty = Path(lbl_dir / "targets.parquet")
        pd.DataFrame(columns=["date","ticker","y_2x","y_10x","rel_1M","rel_3M","rel_12M",
                              "hit_rel_1M_10p","hit_rel_3M_20p","hit_rel_12M_50p"]).to_parquet(empty, index=False)
        Path(rep_dir/"labels_summary.csv").write_text("empty", encoding="utf-8")
        return

    df_all = pd.concat(rows, ignore_index=True).sort_values(["ticker","date"])
    summ = df_all.agg({
        "y_2x":"mean",
        "y_10x":"mean",
        "hit_rel_1M_10p":"mean",
        "hit_rel_3M_20p":"mean",
        "hit_rel_12M_50p":"mean"
    }).rename("rate").to_frame()
    summ["count_rows"] = len(df_all)

    outp = Path(lbl_dir/"targets.parquet")
    df_all.to_parquet(outp, index=False)
    summ.to_csv(Path(rep_dir/"labels_summary.csv"))

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/labels.yaml")
    args = ap.parse_args()
    main(args.config)
