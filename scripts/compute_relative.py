import pandas as pd
import numpy as np
from pathlib import Path
import yaml
from utils.io_utils import read_parquet, write_parquet, ensure_dir
from utils.calendar_utils import get_sessions, align_to_anchor_calendar
from utils.log_utils import get_logger

logger = get_logger()
HORIZONS = [21, 63, 252]

def load_adj(path: Path, sec: str) -> pd.DataFrame:
    df = read_parquet(path / f"{sec}.parquet")
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date").sort_index()

def fwd_return(adj: pd.Series, h: int) -> pd.Series:
    return adj.shift(-h) / adj - 1.0

def main(cfg_path: str):
    cfg = yaml.safe_load(Path(cfg_path).read_text(encoding="utf-8"))
    proc_dir = Path(cfg["paths"]["proc"])
    out_dir = ensure_dir(proc_dir / "labels")
    reports_dir = ensure_dir(Path(cfg["paths"]["reports"]))

    secs = cfg["universe"]["us"] + cfg["universe"]["jp"]
    spx = cfg["benchmark"]["spx"]
    anchor_cal = cfg["fx"]["anchor_calendar"]
    start, end = cfg["start"], cfg["end"]

    adj_dir = proc_dir / "adj_prices"
    sessions = get_sessions(anchor_cal, start, end)

    spx_df = load_adj(adj_dir, spx)
    spx_df = align_to_anchor_calendar(spx_df, sessions)
    spx_adj = spx_df["adj_close"]

    rows = []
    for sec in secs:
        df = load_adj(adj_dir, sec)
        df = align_to_anchor_calendar(df, sessions)
        adj = df["adj_close"]

        for h in HORIZONS:
            r_stock = fwd_return(adj, h)
            r_spx = fwd_return(spx_adj, h)
            rel = r_stock - r_spx
            tmp = pd.DataFrame({
                "date": adj.index,
                "security_id": sec,
                "h": h,
                "r_stock": r_stock.values,
                "r_spx": r_spx.values,
                "rel_excess": rel.values
            })
            rows.append(tmp)

    labels = pd.concat(rows, ignore_index=True).dropna()
    write_parquet(labels, out_dir / "relative_returns.parquet")
    desc = labels.groupby("h")["rel_excess"].describe()
    desc.to_csv(reports_dir / "relative_returns_summary.csv", index=True)
    logger.info("relative returns saved. summary -> reports/checks/relative_returns_summary.csv")

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/base.yaml")
    args = ap.parse_args()
    main(args.config)
