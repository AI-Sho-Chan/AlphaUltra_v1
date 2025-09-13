import pandas as pd
from pathlib import Path

def main():
    ds_p = Path("data/proc/dataset/dataset_text_only.parquet")
    y_p  = Path("data/proc/labels/targets.parquet")
    if not ds_p.exists() or not y_p.exists():
        print("dataset or labels missing"); return
    ds = pd.read_parquet(ds_p); y = pd.read_parquet(y_p)
    df = ds.merge(y, on=["ticker","date"], how="inner")
    (ds_p.parent).mkdir(parents=True, exist_ok=True)
    out = ds_p.parent/"dataset_final.parquet"
    df.to_parquet(out, index=False)
    print(f"final rows {len(df)} cols {df.shape[1]} -> {out}")
if __name__ == "__main__": main()
