#!/usr/bin/env python
"""
EDINET daily ingest skeleton.

Reads EDINET_SUBSCRIPTION_KEY from env or .env.local via client,
creates a date-stamped folder under data/raw/edinet, and writes
a placeholder manifest JSON.
"""
import argparse
from pathlib import Path
from datetime import datetime, date
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src.ingestion.edinet_v2_client import EdinetV2Client


RAW_DIR = ROOT / "data" / "raw" / "edinet"


def parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def main():
    ap = argparse.ArgumentParser(description="EDINET v2 daily ingest (skeleton)")
    ap.add_argument("--date", default=(datetime.now().date()).strftime("%Y-%m-%d"), help="Date YYYY-MM-DD (default: today)")
    args = ap.parse_args()

    d = parse_date(args.date)
    out_dir = RAW_DIR / d.strftime("%Y-%m-%d")
    out_dir.mkdir(parents=True, exist_ok=True)

    client = EdinetV2Client()
    docs = client.get_documents_for_date(d)

    manifest = {
        "date": d.isoformat(),
        "count": len(docs),
        "docs": docs,
        "note": "skeleton run (no network)"
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[edinet] wrote {out_dir / 'manifest.json'} (count={len(docs)})")


if __name__ == "__main__":
    main()

