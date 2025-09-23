import pathlib, pandas as pd, numpy as np, lightgbm as lgb
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score

FE = pathlib.Path("tmp/features_tdnet_q4_smoke.parquet")
OUT = pathlib.Path("reports/checks/tdnet_model_y_2x_oof.parquet")
OUT.parent.mkdir(parents=True, exist_ok=True)

df = pd.read_parquet(FE)
y  = df["y_2x"].astype("int8")
X  = df.select_dtypes(include=[np.number]).copy()
if "y_2x" in X.columns: X.drop(columns=["y_2x"], inplace=True)
X  = X.replace([np.inf,-np.inf], np.nan).fillna(0.0).astype("float32")

pos, neg = int((y==1).sum()), int((y==0).sum())
oof = np.full(len(y), 0.01, dtype="float32")  # デフォルトは低確率

if pos>0 and neg>0:
    n_splits = 5 if len(y)>=50 else 2
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    for tr, va in skf.split(X, y):
        dtr = lgb.Dataset(X.iloc[tr], label=y.iloc[tr])
        dva = lgb.Dataset(X.iloc[va], label=y.iloc[va])
        params = {"objective":"binary","metric":"auc","verbosity":-1}
        bst = lgb.train(
            params, dtr, num_boost_round=50, valid_sets=[dva],
            callbacks=[lgb.log_evaluation(period=0)]
        )
        oof[va] = bst.predict(X.iloc[va])

oof_df = pd.DataFrame({
    "ticker": df["ticker"].astype(str),
    "eff_date": pd.to_datetime(df["eff_date"]).dt.normalize(),
    "y": y.astype("int8"),
    "score": oof
})
oof_df.to_parquet(OUT, index=False)

try:
    auc = roc_auc_score(y, oof) if len(np.unique(y))>1 else None
except Exception:
    auc = None
print({"rows": len(oof_df), "pos": pos, "neg": neg, "auc": auc})
