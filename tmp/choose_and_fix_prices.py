import pathlib, pandas as pd, json, re

root = pathlib.Path("data/proc/prices")
cands = sorted(root.rglob("*.parquet"))
if not cands:
    raise SystemExit({"error":"no parquet under data/proc/prices"})

# 優先度：名前優先→列要件
def score(p: pathlib.Path):
    name = p.name.lower()
    s = 0
    if "jp_prices_std_compat" in name: s += 100
    if "jp_prices_std" in name: s += 50
    if "prices" in name: s += 10
    return (-s, len(str(p)))  # 短いパスを優先

cands = sorted(cands, key=score)

chosen = None
cols_preview = {}
for p in cands:
    try:
        df = pd.read_parquet(p, engine="auto")
        cols = set(df.columns)
        cols_preview[str(p)] = list(df.columns)[:20]
        need_base = {"ticker","date","volume"}
        close_like = [c for c in ("adj_close","px_close","close","Adj Close","adjclose") if c in cols]
        if need_base.issubset(cols) and close_like:
            chosen = p
            # adj_closeが無ければ補完
            if "adj_close" not in cols:
                df["adj_close"] = df[close_like[0]]
                df.to_parquet(p, index=False)
            break
    except Exception as e:
        cols_preview[str(p)] = [f"read_error:{type(e).__name__}"]

if not chosen:
    raise SystemExit({"error":"no suitable prices parquet found", "candidates": cols_preview})

out = {"chosen": str(chosen), "cols": cols_preview[str(chosen)]}
pathlib.Path("tmp").mkdir(exist_ok=True, parents=True)
pathlib.Path("tmp/chosen_prices.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(out)
