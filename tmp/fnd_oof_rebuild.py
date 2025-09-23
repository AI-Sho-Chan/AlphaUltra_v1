import pandas as pd, numpy as np, pathlib
from sklearn.model_selection import StratifiedKFold
from sklearn.ensemble import RandomForestClassifier
FE=r"tmp/features_fnd_2600.parquet"; OUT=r"reports/checks/fnd_y_2x_oof.parquet"
df=pd.read_parquet(FE); y=df["y_2x"].astype("int8")
X=df.select_dtypes(include=[np.number]).drop(columns=["y_2x"],errors="ignore")
keep=X.std(numeric_only=True); X=X[keep[keep>0].index].astype("float32")
oof=np.full(len(y),0.01,dtype="float32")
pos,neg=int((y==1).sum()),int((y==0).sum())
if pos>0 and neg>0 and X.shape[1]>0:
  skf=StratifiedKFold(n_splits=5,shuffle=True,random_state=42)
  for tr,va in skf.split(X,y):
    clf=RandomForestClassifier(n_estimators=600,min_samples_leaf=5,class_weight="balanced",random_state=42,n_jobs=1)
    clf.fit(X.iloc[tr],y.iloc[tr]); oof[va]=clf.predict_proba(X.iloc[va])[:,1]
pathlib.Path(OUT).parent.mkdir(parents=True, exist_ok=True)
pd.DataFrame({"ticker":df["ticker"].astype(str),"eff_date":pd.to_datetime(df["eff_date"]).dt.normalize(),
              "y":y,"p_raw":oof}).to_parquet(OUT,index=False)
print({"rows":len(y),"pos":pos,"nfeat":int(X.shape[1]),"pmax":float(oof.max())})
