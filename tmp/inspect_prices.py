import re, pathlib, json, sys
cfg = pathlib.Path(r"configs/tdnet_2014.yaml").read_text(encoding="utf-8", errors="ignore")
m = re.search(r'(?m)^\s*prices\s*:\s*(.+)$', cfg)
p = pathlib.Path(m.group(1).strip()) if m else None
print({"prices_path": str(p) if p else None})
if p and p.exists():
    import pandas as pd
    df = pd.read_parquet(p)
    print({"cols": list(df.columns)[:20], "n": len(df)})
else:
    print({"note":"prices parquet not found"})
