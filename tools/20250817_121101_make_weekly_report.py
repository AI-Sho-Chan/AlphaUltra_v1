import json, pathlib, datetime

ROOT = pathlib.Path("C:/AI/AlphaUltra")
OUTDIR = ROOT/"reports"/"weekly"
IMGDIR = OUTDIR/"img"

def collect_metrics(n=50):
    items = []
    for p in ROOT.glob("experiments/*/metrics.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            ts = data.get("timestamp", "")
            items.append((ts, p, data))
        except Exception:
            pass
    items.sort(reverse=True, key=lambda x: x[0])
    return items[:n]

def summarize(items):
    sh, pk = [], []
    for _, _, m in items:
        try:
            sh.append(float(m.get("portfolio_metrics",{}).get("sharpe_annualized",0.0)))
            pk.append(float(m.get("signal_metrics",{}).get("precision_at_k",0.0)))
        except Exception:
            pass
    avg_sh = sum(sh)/len(sh) if sh else 0.0
    avg_pk = sum(pk)/len(pk) if pk else 0.0
    return avg_sh, avg_pk, sh, pk

def main():
    items = collect_metrics()
    avg_sh, avg_pk, sh, pk = summarize(items)
    OUTDIR.mkdir(parents=True, exist_ok=True)
    IMGDIR.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    out = OUTDIR / f"{today}_report.md"
    lines = []
    lines.append(f"# Weekly Report ({today})")
    lines.append("")
    lines.append(f"- Experiments scanned: {len(items)}")
    lines.append(f"- Avg Sharpe (annualized): {avg_sh:.3f}")
    lines.append(f"- Avg Precision@K: {avg_pk:.3f}")
    lines.append("")
    lines.append("## Latest Experiments (top 10)")
    lines.append("| exp_id | timestamp | dataset | sharpe | precision@K | path |")
    lines.append("|---|---|---|---:|---:|---|")
    for ts, p, m in items[:10]:
        eid = m.get("exp_id","NA")
        ds = m.get("dataset","NA")
        shv = float(m.get("portfolio_metrics",{}).get("sharpe_annualized",0.0))
        pkv = float(m.get("signal_metrics",{}).get("precision_at_k",0.0))
        lines.append(f"| {eid} | {ts} | {ds} | {shv:.3f} | {pkv:.3f} | {p.parent.name} |")
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"[REPORT] {out}")

if __name__ == "__main__":
    main()

