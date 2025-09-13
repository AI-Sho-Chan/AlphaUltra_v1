import json, csv
from pathlib import Path

import pandas as pd

CFG_REPORTS = Path("reports/checks")
ROOT = Path("data/raw/filings/us")

def row_from_meta(meta_path: Path):
    d = json.loads(meta_path.read_text(encoding="utf-8"))
    return {
        "cik": str(d.get("cik") or "").zfill(10),
        "ticker": d.get("ticker") or "",
        "form": d.get("form") or "",
        "companyName": d.get("companyName") or "",
        "accessionNumber": d.get("accessionNumber") or "",
        "acceptanceDateTime": d.get("acceptanceDateTime") or "",
        "primaryDocument": d.get("primaryDocument") or "",
        "path": str(meta_path.parent)
    }

def main():
    CFG_REPORTS.mkdir(parents=True, exist_ok=True)
    metas = list(ROOT.glob("**/metadata.json"))
    rows = [row_from_meta(p) for p in metas]
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("acceptanceDateTime")
    out = CFG_REPORTS / "filings_summary.csv"
    df.to_csv(out, index=False)
    print(f"wrote {out} rows={len(df)}")

if __name__ == "__main__":
    main()
