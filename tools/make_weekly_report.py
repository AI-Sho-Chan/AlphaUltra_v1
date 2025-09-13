import pathlib, csv, datetime, json, os

ROOT = pathlib.Path(r"C:\AI\AlphaUltra")
COMP_DIR = ROOT / "reports" / "compare"
WEEKLY_DIR = ROOT / "reports" / "weekly"
IMG_DIR = WEEKLY_DIR / "img"
WEEKLY_DIR.mkdir(parents=True, exist_ok=True); IMG_DIR.mkdir(parents=True, exist_ok=True)

def latest_compare_csv():
    cands = sorted(COMP_DIR.glob("*_all_metrics.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    return cands[0] if cands else None

def read_rows(csv_path):
    rows = []
    with csv_path.open(encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append(row)
    return rows

def fnum(x, d=3):
    try:
        return f"{float(x):.{d}f}"
    except: return ""

def to_float(x):
    try: return float(x)
    except: return None

def main():
    cmp = latest_compare_csv()
    stamp = datetime.datetime.now().strftime("%Y-%m-%d")
    out = WEEKLY_DIR / f"{stamp}_report.md"

    if not cmp:
        out.write_text("# Weekly Report\n\n(no compare csv found)\n", encoding="utf-8")
        print("[REPORT]", out); return

    rows = read_rows(cmp)
    # 正規名に寄せる
    for r in rows:
        if "regime" not in r or not r["regime"]:
            r["regime"] = r.get("mask_value") or "(all)"
        # 別名→正規名の最低限フォールバック
        r["precision_at_k"] = r.get("precision_at_k") or r.get("p_at_k")
        r["sharpe_annualized"] = r.get("sharpe_annualized") or r.get("sharpe")
        r["sharpe_annualized_net"] = r.get("sharpe_annualized_net") or r.get("sharpe_net")

    # 概要
    n = len(rows)
    mean_p = sum(to_float(r["precision_at_k"]) for r in rows if to_float(r["precision_at_k"]) is not None) / max(1, sum(1 for r in rows if to_float(r["precision_at_k"]) is not None))
    mean_s_g = sum(to_float(r["sharpe_annualized"]) for r in rows if to_float(r["sharpe_annualized"]) is not None) / max(1, sum(1 for r in rows if to_float(r["sharpe_annualized"]) is not None))
    mean_s_n = sum(to_float(r["sharpe_annualized_net"]) for r in rows if to_float(r["sharpe_annualized_net"]) is not None) / max(1, sum(1 for r in rows if to_float(r["sharpe_annualized_net"]) is not None))

    # Top10：Netでソート
    rows_net = [r for r in rows if to_float(r["sharpe_annualized_net"]) is not None]
    rows_net.sort(key=lambda r: to_float(r["sharpe_annualized_net"]), reverse=True)
    top10 = rows_net[:10]

    # レジーム別Top2：winners_by_regime の最新を拾って差し込み
    wbr_md = ""
    wbr_cands = sorted(COMP_DIR.glob("*_winners_by_regime.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    if wbr_cands:
        wbr_md = wbr_cands[0].read_text(encoding="utf-8")

    # ヒートマップ画像（存在すれば貼る）
    hmap_g = COMP_DIR / "img" / "heatmap_gross.png"
    hmap_n = COMP_DIR / "img" / "heatmap_net.png"

    # MD 組み立て
    lines = []
    lines.append(f"# Weekly Report ({stamp})\n")
    lines.append(f"- Experiments scanned: {n}")
    lines.append(f"- Avg Precision@K: {fnum(mean_p)}")
    lines.append(f"- Avg Sharpe (gross): {fnum(mean_s_g)}")
    lines.append(f"- Avg Sharpe (net): {fnum(mean_s_n)}\n")

    # 画像
    if hmap_g.exists() or hmap_n.exists():
        lines.append("## Regime × K Heatmaps\n")
        if hmap_g.exists(): lines.append(f"![heatmap_gross](../compare/img/heatmap_gross.png)")
        if hmap_n.exists(): lines.append(f"![heatmap_net](../compare/img/heatmap_net.png)")
        lines.append("")

    # Top10 テーブル
    lines.append("## Top 10 by Net Sharpe\n")
    if top10:
        cols = ["exp_id","k","regime","precision_at_k","sharpe_annualized","sharpe_annualized_net","turnover_daily","cost_bps","max_drawdown","path"]
        lines.append("| " + " | ".join(cols) + " |")
        lines.append("|" + "|".join(["---"]*len(cols)) + "|")
        for r in top10:
            lines.append("| " + " | ".join([
                r.get("exp_id",""),
                str(int(float(r["k"])) if r.get("k") else 0),
                r.get("regime",""),
                fnum(r.get("precision_at_k")),
                fnum(r.get("sharpe_annualized")),
                fnum(r.get("sharpe_annualized_net")),
                fnum(r.get("turnover_daily")),
                str(int(float(r["cost_bps"])) if r.get("cost_bps") else "0"),
                fnum(r.get("max_drawdown")),
                r.get("path",""),
            ]) + " |")
    else:
        lines.append("_no rows_")
    lines.append("")

    # レジーム別Top2 の差し込み
    if wbr_md:
        lines.append("## Winners by Regime (Top2)\n")
        lines.append(wbr_md)

    out.write_text("\n".join(lines), encoding="utf-8")
    print("[REPORT]", out)

if __name__ == "__main__":
    main()

