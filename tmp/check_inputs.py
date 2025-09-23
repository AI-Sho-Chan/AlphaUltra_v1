import pathlib, re, pandas as pd
y = pathlib.Path("configs/tdnet_2014.yaml").read_text(encoding="utf-8", errors="ignore")
m = re.search(r'(?m)^\s*prices\s*:\s*(.+)$', y)
p = pathlib.Path(m.group(1).strip()) if m else None
print({"prices_path": str(p) if p else None, "exists": p.exists() if p else None})
if p and p.exists():
    df = pd.read_parquet(p)
    print({"cols": list(df.columns), "rows": len(df), "date_min": str(df["eff_date"].min()), "date_max": str(df["eff_date"].max())})
