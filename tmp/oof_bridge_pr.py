import pandas as pd
p = r"reports/checks/tdnet_model_y_2x_oof.parquet"
df = pd.read_parquet(p)
if "p_raw" not in df.columns:
    if "score" in df.columns:
        df["p_raw"] = df["score"]
    else:
        raise SystemExit({"error":"OOF lacks score/p_raw", "cols":list(df.columns)})
df.to_parquet(p, index=False)
print({"ok":True,"cols":list(df.columns)})
