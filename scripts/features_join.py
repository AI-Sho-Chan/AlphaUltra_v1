
import pandas as pd, numpy as np, yaml, json
from pathlib import Path

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def detect_price_column(df: pd.DataFrame):
    for c in ["adj_close","Adj Close","adjusted_close","close","Close"]:
        if c in df.columns: return c
    num = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if num: return num[0]
    raise ValueError("no price column")

def parse_df_index(df: pd.DataFrame):
    if isinstance(df.index, pd.DatetimeIndex):
        idx = pd.to_datetime(df.index, utc=True, errors="coerce").tz_convert("UTC").floor("D")
        df = df.copy(); df.index = idx; return df
    for c in df.columns:
        if "date" in c.lower():
            df[c] = pd.to_datetime(df[c], utc=True, errors="coerce").dt.tz_convert("UTC").dt.floor("D")
            return df.set_index(c).sort_index()
    raise ValueError("no date column/index")

def quant_from_prices(adj_dir: Path):
    rows=[]
    for f in adj_dir.glob("*.parquet"):
        try:
            df = pd.read_parquet(f)
            df = parse_df_index(df)
            col = detect_price_column(df)
            s = df[col].astype(float)
            r1 = s.pct_change(1)
            r5 = s.pct_change(5)
            r21= s.pct_change(21)
            m63= s.pct_change(63)
            m252= s.pct_change(252)
            vol21 = r1.rolling(21).std()
            vol63 = r1.rolling(63).std()
            out = pd.DataFrame({
                "ticker": f.stem,
                "date": s.index.tz_convert("UTC").floor("D"),
                "ret_1d": r1.values,
                "ret_5d": r5.values,
                "ret_21d": r21.values,
                "mom_63d": m63.values,
                "mom_252d": m252.values,
                "vol_21d": vol21.values,
                "vol_63d": vol63.values,
            })
            rows.append(out)
        except Exception:
            pass
    if not rows:
        return pd.DataFrame(columns=["ticker","date"])
    q = pd.concat(rows, ignore_index=True).dropna().sort_values(["ticker","date"])
    return q

def load_if_exists(p: Path):
    if p.exists():
        return pd.read_parquet(p)
    return pd.DataFrame()

def main(cfg_path: str):
    cfg = yaml.safe_load(Path(cfg_path).read_text(encoding="utf-8"))
    adj_dir = Path(cfg["paths"]["adj_prices_dir"])
    text_dir= Path(cfg["paths"]["text_dir"])
    labels_path = Path(cfg["paths"]["labels_path"])
    out_dir = Path(cfg["paths"]["out_dir"]); ensure_dir(out_dir)
    reports_dir = Path(cfg["paths"]["reports_dir"]); ensure_dir(reports_dir)

    if not labels_path.exists():
        raise SystemExit(f"labels not found: {labels_path}")
    y = pd.read_parquet(labels_path)
    y["date"] = pd.to_datetime(y["date"], utc=True, errors="coerce").dt.tz_convert("UTC").dt.floor("D")

    q = quant_from_prices(adj_dir)

    f_file = text_dir / "filing_event_features.parquet"
    e_file = text_dir / "edinet_doc_features.parquet"
    n_file = text_dir / "news_dict_features.parquet"
    f = load_if_exists(f_file); e = load_if_exists(e_file); n = load_if_exists(n_file)
    for df in [f,e,n]:
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"], utc=True, errors="coerce").dt.tz_convert("UTC").dt.floor("D")

    base = q if not q.empty else pd.DataFrame(columns=["ticker","date"])
    for df in [f,e,n]:
        if df.empty: continue
        if not {"ticker","date"}.issubset(df.columns): continue
        base = base.merge(df, on=["ticker","date"], how="left")
    if not base.empty:
        for c in base.columns:
            if c.endswith(("_1d","_5d","_21d")) or c.startswith(("filing_","count_","edinet_","news_")):
                base[c] = base[c].fillna(0.0)

    Xy = y.merge(base, on=["ticker","date"], how="left")
    feat_cols = [c for c in Xy.columns if c not in ("ticker","date","y_2x","y_10x","ttd_2x","ttd_10x",
                                                    "dd_min_252","rel_1M","rel_3M","rel_12M",
                                                    "hit_rel_1M_10p","hit_rel_3M_20p","hit_rel_12M_50p")]
    if feat_cols:
        mask = Xy[feat_cols].notna().any(axis=1)
        Xy = Xy[mask]
        Xy[feat_cols] = Xy[feat_cols].fillna(0.0)
    out1 = Path(cfg["paths"]["out_dir"]) / "train_dataset.parquet"
    Xy.to_parquet(out1, index=False)

    cols = ["y_2x","hit_rel_1M_10p","hit_rel_3M_20p","hit_rel_12M_50p"]
    summ = {c: float(Xy[c].mean()) for c in cols if c in Xy.columns}
    (reports_dir/"features_join_summary.json").write_text(json.dumps(summ, indent=2), encoding="utf-8")
    print("rows:", len(Xy), "features:", len(feat_cols))

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/model.yaml")
    args = ap.parse_args()
    main(args.config)
