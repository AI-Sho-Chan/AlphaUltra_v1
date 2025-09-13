import json, pathlib, datetime

ROOT = pathlib.Path("C:/AI/AlphaUltra")
rows = []
for p in ROOT.glob("experiments/*/metrics.json"):
    try:
        m = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        continue
    rows.append(
        (
            m.get("timestamp", ""),
            m.get("exp_id", ""),
            float(m.get("portfolio_metrics", {}).get("sharpe_annualized", 0.0)),
            float(m.get("signal_metrics", {}).get("precision_at_k", 0.0)),
            str(p.parent),
        )
    )
rows.sort(reverse=True)
rows = rows[:10]
outdir = ROOT / "reports" / "compare"
outdir.mkdir(parents=True, exist_ok=True)
today = datetime.date.today().isoformat()
md = outdir / f"{today}_conservative_ab.md"
lines = [
    "# Conservative A/B Comparison",
    "",
    "| exp_id | sharpe | P@50 | path |",
    "|---|---:|---:|---|",
]
for _, eid, sh, pk, path in rows:
    lines.append(f"| {eid} | {sh:.3f} | {pk:.3f} | {path} |")
md.write_text("\n".join(lines), encoding="utf-8")
print(f"[COMPARE] {md}")

