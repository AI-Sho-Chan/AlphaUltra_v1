import json, pathlib, sys, argparse, csv

ROOT = pathlib.Path(r"C:\AI\AlphaUltra")
DEFAULT_EXPS = [
    "EXP_2025-08-17_CONSERV_V2",
    "EXP_2025-08-17_CONSERV_V2A",
    "EXP_2025-08-17_CONSERV_V2B",
]


def load_metrics(exp_id: str):
    p = ROOT / "experiments" / exp_id / "metrics.json"
    if not p.exists():
        return exp_id, None, p
    try:
        m = json.loads(p.read_text(encoding="utf-8"))
        sm = m.get("signal_metrics", {}) or {}
        pm = m.get("portfolio_metrics", {}) or {}
        return exp_id, {
            "P@K": sm.get("precision_at_k"),
            "Sharpe": pm.get("sharpe_annualized"),
            "MaxDD": pm.get("max_drawdown"),
        }, p
    except Exception as e:
        return exp_id, {"ERROR": str(e)}, p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("exp_ids", nargs="*")
    ap.add_argument("--csv", default="")
    args = ap.parse_args()

    exp_ids = args.exp_ids or DEFAULT_EXPS
    print("# Inspect metrics")
    rows = []
    for eid in exp_ids:
        eid, res, path = load_metrics(eid)
        print("====", eid)
        if res is None:
            print("  metrics.json NOT FOUND ->", path)
        elif "ERROR" in res:
            print("  ERROR:", res["ERROR"])
        else:
            print(f"  P@K={res['P@K']}  Sharpe={res['Sharpe']}  MaxDD={res['MaxDD']}")
            rows.append({"exp_id": eid, **res})
    print("\n[done]")
    if args.csv:
        p = pathlib.Path(args.csv)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["exp_id","P@K","Sharpe","MaxDD"])
            w.writeheader()
            for r in rows:
                w.writerow(r)
        print("[CSV]", p)


if __name__ == "__main__":
    sys.exit(main() or 0)
