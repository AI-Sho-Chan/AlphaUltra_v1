#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convert Kabutan CSVs (data/raw/kabutan/**/tdnet.csv) into per-event JSON files under
  data/raw/tdnet/YYYY/MM/DD/*.json

JSON fields per event
  {
    ticker: "####.T",
    code4: "####",
    title: str,
    published_at_jst: "YYYY-MM-DDTHH:MM:SS+09:00",
    date: "YYYY-MM-DD",
    event_type: "other",
    url_detail: str | "",
    url_pdf: str | ""
  }

Strict code extraction from the コード column only (4-digit jp code). If invalid, skip.
Always continue on errors; never exit the whole run.
"""

from pathlib import Path
import json
import re
import sys
import pandas as pd


ROOT = Path(".").resolve()
CSV_ROOT = ROOT / "data/raw/kabutan"
OUT_ROOT = ROOT / "data/raw/tdnet"


def to_jst_iso(date_str: str, hm: str) -> str:
    hm = (hm or "").strip()
    if not re.match(r"^\d{1,2}:\d{2}$", hm):
        hm = "00:00"
    # seconds default 00; append +09:00 offset
    return f"{date_str}T{hm}:00+09:00"


def extract_code4(val: str) -> str | None:
    s = (str(val) or "").strip()
    m = re.match(r"^(\d{4})$", s)
    return m.group(1) if m else None


def process_csv(csv_path: Path):
    # date comes from directory name .../YYYY-MM-DD/tdnet.csv
    try:
        ymd = csv_path.parent.name
        assert re.match(r"^\d{4}-\d{2}-\d{2}$", ymd)
    except Exception:
        return 0

    try:
        try:
            df = pd.read_csv(csv_path, dtype=str, encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(csv_path, dtype=str, encoding="utf-8-sig")
    except Exception:
        return 0

    col_code = None
    for c in df.columns:
        if c.strip() in ("コード", "code", "ｺｰﾄﾞ"):
            col_code = c
            break
    col_title = None
    for c in df.columns:
        if c.strip() in ("タイトル", "title"):
            col_title = c
            break
    col_time = None
    for c in df.columns:
        if c.strip() in ("掲載時刻", "時刻", "time"):
            col_time = c
            break
    col_url = None
    for c in df.columns:
        if c.strip() in ("URL", "url"):
            col_url = c
            break

    if not col_code:
        return 0

    out_dir = OUT_ROOT / ymd[:4] / ymd[5:7] / ymd[8:10]
    out_dir.mkdir(parents=True, exist_ok=True)

    n = 0
    for i, row in df.iterrows():
        code4 = extract_code4(row.get(col_code, ""))
        if not code4:
            continue
        title = str(row.get(col_title, "")).strip() if col_title else ""
        hm = str(row.get(col_time, "")).strip() if col_time else ""
        url = str(row.get(col_url, "")).strip() if col_url else ""

        data = {
            "ticker": f"{code4}.T",
            "code4": code4,
            "title": title,
            "published_at_jst": to_jst_iso(ymd, hm),
            "date": ymd,
            "event_type": "other",
            "url_detail": url,
            "url_pdf": "",
        }
        # Avoid collisions by indexing events per day/code
        out = out_dir / f"{code4}_{i:03d}.json"
        out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        n += 1
    return n


def main():
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    total = 0
    for csv_path in sorted(CSV_ROOT.rglob("tdnet.csv")):
        try:
            total += process_csv(csv_path)
        except Exception as e:
            # Per spec: continue on errors
            sys.stderr.write(f"[csv2json] error {csv_path}: {e}\n")
            continue
    print(f"[csv2json] wrote events: {total}")


if __name__ == "__main__":
    main()

