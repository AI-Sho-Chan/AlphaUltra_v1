import json, pathlib, datetime, collections

ROOT = pathlib.Path("C:/AI/AlphaUltra")
rows = []
for p in ROOT.glob("experiments/*/metrics.json"):
    try:
        m = json.loads(p.read_text(encoding="utf-8"))
        rows.append({
            "exp_id": m.get("exp_id", ""),
            "k": m.get("k", ""),
            "regime": (m.get("filters") or {}).get("mask_value", "(all)"),
            "p_at_k": m.get("signal_metrics", {}).get("precision_at_k", 0.0),
            "sharpe": m.get("portfolio_metrics", {}).get("sharpe_annualized", 0.0),
            "maxdd": m.get("portfolio_metrics", {}).get("max_drawdown", 0.0),
        })
    except Exception:
        pass

Agg = collections.defaultdict(lambda: collections.defaultdict(list))
for r in rows:
    Agg[(r["exp_id"], r["k"])][r["regime"]].append(r)

lines = [
    "# Regime Summary",
    "",
    "| exp_id | k | regime | sharpe | P@K | maxDD |",
    "|---|---:|---|---:|---:|---:|",
]
for (eid, k), mp in sorted(Agg.items()):
    for regime, arr in mp.items():
        if not arr:
            continue
        s = lambda key: sum(x[key] for x in arr) / len(arr)
        lines.append(f"| {eid} | {k} | {regime} | {s('sharpe'):.3f} | {s('p_at_k'):.3f} | {s('maxdd'):.3f} |")

outdir = ROOT / "reports" / "compare"
outdir.mkdir(parents=True, exist_ok=True)
md = outdir / f"{datetime.date.today().isoformat()}_regimes.md"
md.write_text("\n".join(lines), encoding="utf-8")
print(f"[REGIME-SUMMARY] {md}")

