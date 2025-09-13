import csv, pathlib, datetime
import matplotlib.pyplot as plt

ROOT = pathlib.Path("C:/AI/AlphaUltra")
cmpdir = ROOT / "reports" / "compare"
imgdir = cmpdir / "img"
imgdir.mkdir(parents=True, exist_ok=True)

def load_latest_csv():
    cands = sorted(cmpdir.glob("*_all_metrics.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    return cands[0] if cands else None

def build_pivot(rows, value_key):
    # regimes on x, K on y
    regimes = ["(all)", "bull_lowvol", "bear_highvol"]
    ks = [30, 50, 100]
    grid = [[None for _ in regimes] for __ in ks]
    for r in rows:
        try:
            k = int(r.get("k") or 0)
            reg = r.get("mask_value", "(all)")
            if k in ks and reg in regimes:
                i = ks.index(k); j = regimes.index(reg)
                grid[i][j] = float(r.get(value_key) or 0.0)
        except Exception:
            pass
    return ks, regimes, grid

def draw_heatmap(rows, value_key, out_path, title):
    ks, regimes, grid = build_pivot(rows, value_key)
    if not any(any(v is not None for v in row) for row in grid):
        return False
    data = [[(v if v is not None else 0.0) for v in row] for row in grid]
    plt.figure(figsize=(6, 4))
    plt.imshow(data, aspect='auto')
    plt.title(title)
    plt.xticks(range(len(regimes)), regimes)
    plt.yticks(range(len(ks)), [str(k) for k in ks])
    plt.colorbar()
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()
    return True

def main():
    csvp = load_latest_csv()
    if not csvp:
        print("[HEATMAP] no compare_all csv; skip")
        return 0
    rows = []
    with open(csvp, newline='', encoding='utf-8') as f:
        r = csv.DictReader(f)
        rows = list(r)
    ok1 = draw_heatmap(rows, 'sharpe', imgdir / 'heatmap_gross.png', 'Sharpe (gross)')
    ok2 = draw_heatmap(rows, 'sharpe_net', imgdir / 'heatmap_net.png', 'Sharpe (net)')
    print("[HEATMAP]", "gross" if ok1 else "-", "/", "net" if ok2 else "-")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())

