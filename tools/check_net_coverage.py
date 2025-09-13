import pathlib, csv

ROOT = pathlib.Path(r"C:\AI\AlphaUltra")
cmp_dir = ROOT / "reports" / "compare"
csvs = sorted(cmp_dir.glob("*_all_metrics.csv"), key=lambda p:p.stat().st_mtime, reverse=True)
if not csvs:
    print("[CHECK] no compare csv found"); raise SystemExit(1)

p = csvs[0]
rows = list(csv.DictReader(p.open(encoding="utf-8")))
ok = [r for r in rows if r.get("sharpe_annualized_net") not in (None,"","NaN")]
miss = [r for r in rows if r.get("sharpe_annualized_net") in (None,"","NaN")]

print("[CHECK] CSV:", p)
print("[CHECK] rows:", len(rows), " net_present:", len(ok), " net_missing:", len(miss))
if miss:
    print("[CHECK] missing exp_ids (first 10):", [r.get("exp_id") for r in miss[:10]])

