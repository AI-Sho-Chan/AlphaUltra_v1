import yaml
from pathlib import Path
import json, csv, datetime

def main(cfg_path: str):
    cfg = yaml.safe_load(Path(cfg_path).read_text(encoding="utf-8"))
    raw_dir = Path(cfg["paths"]["raw"]) / "filings" / "us"
    rows = []
    for cik_dir in sorted(raw_dir.glob("*")):
        for acc_dir in sorted(cik_dir.glob("*")):
            md = acc_dir / "metadata.json"
            if md.exists():
                d = json.loads(md.read_text(encoding="utf-8"))
                d["has_primary"] = any(p.exists() for p in acc_dir.iterdir() if p.name != "metadata.json")
                rows.append(d)
    out = Path(cfg["paths"]["reports"]) / "filings_summary.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["ticker","cik","form","accessionNumber","acceptanceDateTime","primaryDocument","has_primary","source"])
        w.writeheader()
        for r in sorted(rows, key=lambda x: x["acceptanceDateTime"], reverse=True):
            w.writerow(r)

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/filings.yaml")
    a = ap.parse_args()
    main(a.config)
