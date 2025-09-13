#!/usr/bin/env python
"""
TDNET daily ingest skeleton.

Backends:
  - jpx_api: placeholder (no network in sandbox)
  - local_csv: reads CSVs under data/raw/tdnet/YYYY-MM-DD/*.csv (if present)
"""
import argparse
from pathlib import Path
from datetime import datetime, date
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src.ingestion.tdnet_client import TdnetClient


RAW_DIR = ROOT / "data" / "raw" / "tdnet"


def parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def main():
    ap = argparse.ArgumentParser(description="TDNET daily ingest (skeleton)")
    ap.add_argument("--date", default=(datetime.now().date()).strftime("%Y-%m-%d"), help="Date YYYY-MM-DD (default: today)")
    ap.add_argument("--backend", choices=["jpx_api", "local_csv"], default="jpx_api", help="Ingest backend")
    args = ap.parse_args()

    d = parse_date(args.date)
    out_dir = RAW_DIR / d.strftime("%Y-%m-%d")
    out_dir.mkdir(parents=True, exist_ok=True)

    client = TdnetClient(root=ROOT, backend=args.backend)
    items = client.fetch_day(d)

    manifest = {
        "date": d.isoformat(),
        "backend": args.backend,
        "count": len(items),
        "items": items,
        "note": "skeleton run"
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[tdnet] wrote {out_dir / 'manifest.json'} (count={len(items)}, backend={args.backend})")


if __name__ == "__main__":
    main()

