import pandas as pd
from pathlib import Path
import yaml
from utils.io_utils import ensure_dir, read_parquet, write_parquet
from utils.log_utils import get_logger

logger = get_logger()

def manual_adjust_close(df: pd.DataFrame, acts: pd.DataFrame | None) -> pd.Series:
    df = df.sort_values("date").copy()
    df["date"] = pd.to_datetime(df["date"])
    close = df.set_index("date")["close"].astype(float)
    fac = pd.Series(1.0, index=close.index)
    if acts is not None and not acts.empty:
        acts = acts.copy()
        acts["date"] = pd.to_datetime(acts["date"])
        acts = acts.set_index("date").sort_index()
        if "split_ratio" in acts.columns:
            sr = acts["split_ratio"].dropna()
            sr = sr[sr != 0]
            fac_s = pd.Series(1.0, index=close.index)
            fac_s.loc[sr.index.intersection(fac_s.index)] = 1.0 / sr
            fac = fac * fac_s[::-1].cumprod()[::-1]
        if "dividend" in acts.columns:
            dv = acts["dividend"].dropna()
            dv = dv[dv != 0]
            if not dv.empty:
                prev_close = close.shift(1)
                fac_d = pd.Series(1.0, index=close.index)
                for d, cash in dv.items():
                    if d in fac_d.index and pd.notna(prev_close.loc[d]) and prev_close.loc[d] > 0:
                        fac_d.loc[d] = (prev_close.loc[d] - cash) / prev_close.loc[d]
                fac = fac * fac_d[::-1].cumprod()[::-1]
    adj = close * fac
    return adj

def main(cfg_path: str):
    cfg = yaml.safe_load(Path(cfg_path).read_text(encoding="utf-8"))
    raw_dir = Path(cfg["paths"]["raw"])
    proc_dir = Path(cfg["paths"]["proc"])
    use_vendor = cfg["vendor"]["use_vendor_adjclose_first"]

    px_dir = raw_dir / "prices"
    ac_dir = raw_dir / "actions"
    out_dir = ensure_dir(proc_dir / "adj_prices")

    for fp in px_dir.glob("*.parquet"):
        sec = fp.stem
        df = read_parquet(fp)
        acts = None
        ac_fp = ac_dir / f"{sec}.parquet"
        if ac_fp.exists():
            acts = read_parquet(ac_fp)

        if use_vendor and "adj_close" in df.columns and df["adj_close"].notna().any():
            adj = df[["date","adj_close"]].copy()
            adj["security_id"] = sec
        else:
            adj_series = manual_adjust_close(df, acts)
            adj = adj_series.reset_index().rename(columns={"index":"date",0:"adj_close"})
            adj["security_id"] = sec

        write_parquet(adj, out_dir / f"{sec}.parquet")

    logger.info("adjusted prices saved.")

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/base.yaml")
    args = ap.parse_args()
    main(args.config)
