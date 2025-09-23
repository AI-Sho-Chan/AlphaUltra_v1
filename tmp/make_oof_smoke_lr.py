import pathlib, pandas as pd, numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler

FE="tmp/features_tdnet_q4_smoke.parquet"  # 400行に更新後を使用
OUT="reports/checks/tdnet_model_y_2x_oof.parquet"
df=pd.read_parquet(FE)
y=df["y_2x"].astype("int8")
X=df.select_dtypes(include=[np.number]).drop(columns=[c for c in ["y_2x"] if c in df.columns], errors="ignore")
X=X.replace([np.inf,-np.inf], np.nan).fillna(0.0).astype("float32")

pos,neg=int((y==1).sum()),int((y==0).sum())
oof=np.full(len(y),0.01,dtype="float32")
if pos>0 and neg>0:
  skf=StratifiedKFold(n_splits=5 if len(y)>=100 else 3, shuffle=True, random_state=42)
  for tr,va in skf.split(X,y):
    ss=StandardScaler().fit(X.iloc[tr])
    Xtr=ss.transform(X.iloc[tr]); Xva=ss.transform(X.iloc[va])
    clf=LogisticRegression(max_iter=2000, class_weight="balanced", n_jobs=1)
    clf.fit(Xtr, y.iloc[tr])
    oof[va]=clf.predict_proba(Xva)[:,1]

o=pd.DataFrame({"ticker":df["ticker"].astype(str),
                "eff_date":pd.to_datetime(df["eff_date"]).dt.normalize(),
                "y":y,"score":oof,"p_raw":oof})
pathlib.Path(OUT).parent.mkdir(parents=True, exist_ok=True)
o.to_parquet(OUT, index=False)
print({"rows":len(o),"pos":pos,"neg":neg,"p_min":float(oof.min()),"p_max":float(oof.max())})
