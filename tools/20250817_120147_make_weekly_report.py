import json, pathlib, datetime

ROOT = pathlib.Path("C:/AI/AlphaUltra")
OUTDIR = ROOT / "reports" / "weekly"


def collect_metrics(n: int = 10):
    items = []
    for p in ROOT.glob("experiments/*/metrics.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            ts = data.get("timestamp", "")
            items.append((ts, p, data))
        except Exception:
            continue
    items.sort(reverse=True, key=lambda x: x[0])
    return items[:n]


def summarize(items):
    sharpe = []
    p_at_k = []
    ok = 0
    ng = 0
    for _, _, m in items:
        try:
            sharpe.append(float(m.get("portfolio_metrics", {}).get("sharpe_annualized", 0.0)))
            p_at_k.append(float(m.get("signal_metrics", {}).get("precision_at_k", 0.0)))
            ok += 1
        except Exception:
            ng += 1
    avg_sharpe = sum(sharpe) / len(sharpe) if sharpe else 0.0
    avg_p_at_k = sum(p_at_k) / len(p_at_k) if p_at_k else 0.0
    return ok, ng, avg_sharpe, avg_p_at_k


def main():
    items = collect_metrics(n=10)
    ok, ng, avg_sharpe, avg_p_at_k = summarize(items)
    OUTDIR.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    out = OUTDIR / f"{today}_report.md"

    lines = []
    lines.append(f"# Weekly Report ({today})")
    lines.append("")
    lines.append(f"- Experiments scanned: {ok + ng} (OK={ok}, NG={ng})")
    lines.append(f"- Avg Sharpe (annualized): {avg_sharpe:.3f}")
    lines.append(f"- Avg Precision@K: {avg_p_at_k:.3f}")
    lines.append("")
    lines.append("## Latest Experiments")
    lines.append("| exp_id | timestamp | dataset | sharpe | precision@K |")
    lines.append("|---|---|---|---:|---:|")
    for ts, p, m in items:
        eid = m.get("exp_id", "NA")
        ds = m.get("dataset", "NA")
        sh = float(m.get("portfolio_metrics", {}).get("sharpe_annualized", 0.0))
        pk = float(m.get("signal_metrics", {}).get("precision_at_k", 0.0))
        lines.append(f"| {eid} | {ts} | {ds} | {sh:.3f} | {pk:.3f} |")

    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"[WEEKLY] Wrote {out}")


if __name__ == "__main__":
    main()

