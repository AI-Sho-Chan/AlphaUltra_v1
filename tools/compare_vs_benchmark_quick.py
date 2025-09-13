import pathlib, pandas as pd

ROOT = pathlib.Path(r"C:\AI\AlphaUltra")
CMP  = ROOT / "reports" / "compare"
ALL  = sorted(CMP.glob("*_all_metrics.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
if not ALL:
    raise SystemExit("[EXCESS] no *_all_metrics.csv found")
latest = ALL[0]

# ベンチ Sharpe（SP500を採用、なければ0）
bench_sharpe = 0.0
bpath = ROOT / "data" / "aux" / "benchmarks.csv"
if bpath.exists():
    bdf = pd.read_csv(bpath)
    col = "SP500" if "SP500" in bdf.columns else None
    if col is not None:
        r = pd.Series(bdf[col]).pct_change().dropna()
        if r.std() > 0:
            bench_sharpe = (r.mean() / r.std()) * (252 ** 0.5)

df = pd.read_csv(latest)
net_col = "sharpe_annualized_net" if "sharpe_annualized_net" in df.columns else ("sharpe_net" if "sharpe_net" in df.columns else None)
if net_col is None:
    raise SystemExit("[EXCESS] net sharpe column not found in all_metrics")

df["bench_sharpe"]  = bench_sharpe
df["excess_sharpe"] = df[net_col] - bench_sharpe

out = CMP / (latest.stem.replace("_all_metrics","") + ".excess.csv")
df.to_csv(out, index=False, encoding="utf-8")
print(f"[EXCESS] wrote {out} (bench_sharpe={bench_sharpe:.3f})")
