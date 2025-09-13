import re, json, time
from pathlib import Path

root = Path(r"C:\AI\AlphaUltra_v1")
raw  = root/"data/raw"
cur  = raw/"tdnet"
cands = [p for p in raw.iterdir() if p.is_dir() and (p.name=="tdnet" or p.name.startswith("tdnet_bak_"))]
def scan(dirp: Path):
    cnt = 0; dmin=None; dmax=None
    rgx = re.compile(r"(20\d{2})[\\/](\d{2})[\\/](\d{2})")
    for p in dirp.rglob("*.json"):
        cnt += 1
        m = rgx.search(str(p))
        if m:
            d = "-".join(m.groups())
            if dmin is None or d<dmin: dmin=d
            if dmax is None or d>dmax: dmax=d
    return {"name": dirp.name, "path": str(dirp), "count": cnt, "date_min": dmin, "date_max": dmax}

stats = [scan(p) for p in cands]
# ベスト選定：2013-09-01 以前を含み 2024-09-10 以降まであるものを優先、同条件なら件数最大
def score(s):
    ok_span = int((s["date_min"] or "9999-99-99") <= "2013-09-01" and (s["date_max"] or "0000-00-00") >= "2024-09-10")
    return (ok_span, s["count"])
best = sorted(stats, key=score, reverse=True)[0] if stats else None

ops = {"chosen": best, "all": stats}
if best and best["name"]!="tdnet":
    ts = time.strftime("%Y%m%d%H%M%S")
    cur_bak = raw/f"tdnet_bak_autosave_{ts}"
    if cur.exists():
        cur.rename(cur_bak)
    Path(best["path"]).rename(cur)
    ops["restored_from"] = best["name"]
    ops["current"] = scan(cur)
print(json.dumps(ops, ensure_ascii=False))
