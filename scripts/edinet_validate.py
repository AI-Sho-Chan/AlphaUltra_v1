import json
from pathlib import Path
import pandas as pd
from utils.io_utils import ensure_dir
from utils.log_utils import get_logger

logger = get_logger()

def main(cfg_path: str):
    import yaml
    cfg = yaml.safe_load(Path(cfg_path).read_text(encoding="utf-8"))
    root = Path(cfg["paths"]["root"])
    reports = Path(cfg["paths"]["reports"])
    rows = []
    for meta in root.glob("**/metadata.json"):
        try:
            d = json.loads(meta.read_text(encoding="utf-8"))
            rows.append({
                "docID": d.get("docID"),
                "edinetCode": d.get("edinetCode"),
                "secCode": d.get("secCode"),
                "filerName": d.get("filerName"),
                "docTypeCode": d.get("docTypeCode"),
                "docDescription": d.get("docDescription"),
                "submitDateTime": d.get("submitDateTime"),
                "path": str(meta.parent)
            })
        except Exception as e:
            logger.warning(f"bad meta {meta}: {e}")
    df = pd.DataFrame(rows)
    ensure_dir(reports)
    out = Path(reports) / "edinet_summary.csv"
    df.sort_values("submitDateTime").to_csv(out, index=False, encoding="utf-8")
    logger.info(f"edinet_summary rows={len(df)} -> {out}")

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/edinet.yaml")
    args = ap.parse_args()
    main(args.config)
