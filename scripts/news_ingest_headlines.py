import feedparser, yaml
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from utils.io_utils import ensure_dir, write_parquet, now_utc_str
from utils.log_utils import get_logger

logger = get_logger()

def main(cfg_path: str):
    cfg = yaml.safe_load(Path(cfg_path).read_text(encoding="utf-8"))
    root = Path(cfg["paths"]["root"]); reports = Path(cfg["paths"]["reports"])
    root.mkdir(parents=True, exist_ok=True)
    rows = []
    for src in cfg["sources"]:
        name=src["name"]; url=src["url"]
        try:
            feed = feedparser.parse(url)
            for e in feed.entries:
                published = None
                for key in ("published_parsed","updated_parsed"):
                    v = e.get(key)
                    if v: 
                        published = datetime(*v[:6], tzinfo=timezone.utc)
                        break
                rows.append({
                    "source": name,
                    "title": e.get("title",""),
                    "summary": e.get("summary",""),
                    "link": e.get("link",""),
                    "published_at": published.isoformat() if published else None,
                    "asof_ts": now_utc_str(),
                })
        except Exception as ex:
            logger.warning(f"feed fail {name}: {ex}")
    df = pd.DataFrame(rows).drop_duplicates(subset=["source","title","link"])
    write_parquet(df, root / "headlines.parquet")
    reports.mkdir(parents=True, exist_ok=True)
    df.sort_values("published_at").tail(50).to_csv(reports/"news_summary.csv", index=False, encoding="utf-8")
    logger.info(f"news rows={len(df)}")

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/news.yaml")
    args = ap.parse_args()
    main(args.config)
