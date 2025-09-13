from pathlib import Path
import pandas as pd
from utils.io_utils import read_parquet
from utils.log_utils import get_logger

logger = get_logger()

def main(cfg_path: str):
    import yaml
    cfg = yaml.safe_load(Path(cfg_path).read_text(encoding="utf-8"))
    root = Path(cfg["paths"]["root"]); reports = Path(cfg["paths"]["reports"])
    pf = root / "headlines.parquet"
    if not pf.exists():
        raise SystemExit(f"missing {pf}")
    df = read_parquet(pf)
    agg = df.groupby("source").size().reset_index(name="count").sort_values("count", ascending=False)
    (reports/"news_counts.csv").parent.mkdir(parents=True, exist_ok=True)
    agg.to_csv(reports/"news_counts.csv", index=False, encoding="utf-8")
    logger.info(f"news sources={len(agg)} total={len(df)}")

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/news.yaml")
    args = ap.parse_args()
    main(args.config)
