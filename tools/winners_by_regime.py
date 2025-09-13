# === root shim ===
import sys
from pathlib import Path
sys.path.insert(0, str((Path(__file__).resolve().parents[1] / "src")))
from alphaultra.utils.root import project_root
CMP = project_root() / "reports" / "compare"
import argparse, pathlib, pandas as pd

def latest_all_metrics():
    p = pathlib.Path("reports/compare").glob("*_all_metrics.csv")
    return max(p, key=lambda x: x.stat().st_mtime)

KEYMAP = {"sharpe":"sharpe_annualized","sharpe_net":"sharpe_annualized_net","p_at_k":"precision_at_k"}

def num(df, col): 
    if col in df.columns: df[col] = pd.to_numeric(df[col], errors="coerce")

ap = argparse.ArgumentParser()
ap.add_argument("--key", default="sharpe_annualized_net")
ap.add_argument("--topn", type=int, default=2)
ap.add_argument("--max_turnover", type=float)
ap.add_argument("--min_p_at_k", type=float)
ap.add_argument("--max_dd", type=float)
args = ap.parse_args()

src = latest_all_metrics()
df  = pd.read_csv(src)
for c in ["precision_at_k","sharpe_annualized","sharpe_annualized_net","turnover_daily","cost_bps","max_drawdown"]:
    num(df, c)
key = KEYMAP.get(args.key, args.key)

# 品質フィルタ（任意）
if args.max_turnover is not None and "turnover_daily" in df: df = df[df["turnover_daily"] <= args.max_turnover]
if args.min_p_at_k is not None: df = df[df["precision_at_k"] >= args.min_p_at_k]
if args.max_dd       is not None: df = df[df["max_drawdown"]    >= args.max_dd]

# 存在するレジームを抽出（空文字は (all)）
regs = df["mask_value"].fillna("").astype(str)
uniq = [""] + sorted([r for r in regs.unique().tolist() if r!=""])

cols = ["exp_id","k","mask_value","precision_at_k","sharpe_annualized","sharpe_annualized_net","turnover_daily","cost_bps","max_drawdown","path"]
for c in cols:
    if c not in df.columns: df[c] = ""

lines = ["# Winners by Regime", f"- source: {src.name}", f"- key: {key}", ""]
for r in uniq:
    view = df[df["mask_value"].fillna("").astype(str)==r].sort_values(key, ascending=False).head(args.topn).copy()
    title = "(all)" if r=="" else r
    lines += [f"## {title}", ""]
    if len(view)==0:
        lines += ["(no data)", ""]
        continue
    v = view.copy()
    v["mask_value"] = v["mask_value"].fillna("").apply(lambda s: "(all)" if str(s).strip()=="" else s)
    lines += ["| " + " | ".join(cols) + " |", "|---|---|---|---|---|---|---|---|---|---|"]
    for _,row in v.iterrows():
        lines += ["| " + " | ".join(str(row.get(c,"")) for c in cols) + " |"]
    lines += [""]

out = pathlib.Path("reports/compare") / (src.name.replace("_all_metrics.csv","_winners_by_regime.md"))
out.write_text("\n".join(lines), encoding="utf-8")
print(f"[WINNERS-BY-REGIME] {out}")

