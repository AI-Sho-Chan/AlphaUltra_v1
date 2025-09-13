import pathlib, pandas as pd, datetime as dt

ROOT = pathlib.Path(r"C:\AI\AlphaUltra")
CMP  = ROOT / "reports" / "compare"
AUX  = ROOT / "data" / "aux"

def latest_csv(glob):
    xs = sorted(CMP.glob(glob), key=lambda p: p.stat().st_mtime, reverse=True)
    return xs[0] if xs else None

allm = latest_csv("*_all_metrics.csv")
if not allm:
    raise SystemExit("[EXCESS-TOP] no all_metrics found")

# ベンチ Sharpe（SP500）
bench = 0.0
bpath = AUX / "benchmarks.csv"
if bpath.exists():
    bdf = pd.read_csv(bpath)
    if "SP500" in bdf.columns:
        r = pd.Series(bdf["SP500"]).pct_change().dropna()
        if r.std() > 0:
            bench = (r.mean()/r.std())*(252**0.5)

df = pd.read_csv(allm)
net = "sharpe_annualized_net" if "sharpe_annualized_net" in df.columns else ("sharpe_net" if "sharpe_net" in df.columns else None)
if net is None:
    raise SystemExit("[EXCESS-TOP] net sharpe col missing")

reg_col = "mask_value" if "mask_value" in df.columns else "regime"
if reg_col not in df.columns:
    df[reg_col] = "(all)"

df["excess_sharpe"] = df[net] - bench

# RegimeごとTop-N
topn = 2
out = CMP / (allm.stem.replace("_all_metrics","") + "_winners_excess.md")
lines = []
lines.append("# Winners by Excess Sharpe")
lines.append(f"- source: {allm.name}")
lines.append(f"- benchmark(SP500) Sharpe: {bench:.3f}")
regs = sorted(df[reg_col].fillna("(all)").unique(), key=lambda x: ("" if x=="(all)" else x))
for rg in regs:
    sub = df[df[reg_col].fillna("(all)")==rg].copy()
    sub = sub.sort_values("excess_sharpe", ascending=False).head(topn)
    lines.append("")
    lines.append(f"## {rg}")
    if sub.empty:
        lines.append("_no entries_")
        continue
    keep = ["exp_id","k",reg_col,"precision_at_k","sharpe_annualized","sharpe_annualized_net","excess_sharpe","turnover_daily","cost_bps","max_drawdown","path"]
    show = [c for c in keep if c in sub.columns]
    lines.append("| " + " | ".join(show) + " |")
    lines.append("|" + "|".join(["---"]*len(show)) + "|")
    for _,r in sub.iterrows():
        lines.append("| " + " | ".join(str(r[c]) for c in show) + " |")

out.write_text("\n".join(lines), encoding="utf-8")
print(f"[EXCESS-TOP] wrote {out}")
