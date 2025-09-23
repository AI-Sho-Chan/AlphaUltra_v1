import pathlib, pandas as pd, numpy as np
from sklearn.model_selection import StratifiedKFold
from sklearn.ensemble import RandomForestClassifier

FE="tmp/features_tdnet_q4_smoke.parquet"
OUT="reports/checks/tdnet_model_y_2x_oof.parquet"
df=pd.read_parquet(FE)
y=df["y_2x"].astype("int8")
X=df.select_dtypes(include=[np.number]).drop(columns=[c for c in ["y_2x"] if c in df.columns], errors="ignore")
# 定数列を除去
std=X.std(numeric_only=True); keep=std[std>0].index.tolist()
X=X[keep].fillna(0.0).astype("float32")

pos,neg=int((y==1).sum()),int((y==0).sum())
oof=np.full(len(y),0.01,dtype="float32")
if pos>0 and neg>0 and X.shape[1]>0:
  skf=StratifiedKFold(n_splits=5 if len(y)>=100 else 3, shuffle=True, random_state=42)
  for tr,va in skf.split(X,y):
    clf=RandomForestClassifier(
      n_estimators=300, max_depth=None, min_samples_leaf=5, class_weight="balanced",
      n_jobs=1, random_state=42
    )
    clf.fit(X.iloc[tr], y.iloc[tr])
    oof[va]=clf.predict_proba(X.iloc[va])[:,1]

o=pd.DataFrame({"ticker":df["ticker"].astype(str),
                "eff_date":pd.to_datetime(df["eff_date"]).dt.normalize(),
                "y":y,"score":oof,"p_raw":oof})
pathlib.Path(OUT).parent.mkdir(parents=True, exist_ok=True)
o.to_parquet(OUT, index=False)
print({"rows":len(o),"pos":pos,"neg":neg,"p_min":float(oof.min()),"p_max":float(oof.max()),"n_features":int(X.shape[1])})
