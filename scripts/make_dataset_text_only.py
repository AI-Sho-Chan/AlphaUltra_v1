import pandas as pd
from pathlib import Path

def load_feature(p: Path):
    if not p.exists():
        return pd.DataFrame(columns=["ticker","date"]).set_index(["ticker","date"])
    df = pd.read_parquet(p)
    if "date" in df.columns: df["date"] = df["date"].astype(str)
    return df.set_index(["ticker","date"])

def main():
    root = Path("data/proc/features_text")
    out  = Path("data/proc/dataset"); out.mkdir(parents=True, exist_ok=True)
    files = ["filing_event_features.parquet","edinet_doc_features.parquet","news_dict_features.parquet"]
    dfs = [load_feature(root/f) for f in files]
    X = dfs[0]
    for d in dfs[1:]: X = X.join(d, how="outer")
    X = X.fillna(0).reset_index()
    X.to_parquet(out/"dataset_text_only.parquet", index=False)
    print(f"rows {len(X)} cols {X.shape[1]}")
if __name__ == "__main__": main()
