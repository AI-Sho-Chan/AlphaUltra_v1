import pandas as pd, numpy as np
evt=pd.read_parquet("reports/checks/tdnet_model_y_2x_oof.parquet")[["ticker","eff_date","y","p_raw"]].rename(columns={"p_raw":"p_evt"})
fnd=pd.read_parquet("reports/checks/fnd_y_2x_oof.parquet")[["ticker","eff_date","p_raw"]].rename(columns={"p_raw":"p_fnd"})
m=evt.merge(fnd,on=["ticker","eff_date"],how="inner",validate="1:1")
m["p_min"]=m[["p_evt","p_fnd"]].min(axis=1); m["p_max"]=m[["p_evt","p_fnd"]].max(axis=1); m["p_diff"]=(m["p_evt"]-m["p_fnd"]).abs()
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
y=m["y"].astype("int8"); X=m[["p_evt","p_fnd","p_min","p_max","p_diff"]].astype("float32")
oof=np.full(len(y),0.01,dtype="float32"); skf=StratifiedKFold(n_splits=5,shuffle=True,random_state=42)
for tr,va in skf.split(X,y):
  ss=StandardScaler().fit(X.iloc[tr]); Xtr=ss.transform(X.iloc[tr]); Xva=ss.transform(X.iloc[va])
  clf=LogisticRegression(max_iter=2000,class_weight="balanced"); clf.fit(Xtr,y.iloc[tr]); oof[va]=clf.predict_proba(Xva)[:,1]
pd.DataFrame({"ticker":m["ticker"].astype(str),"eff_date":pd.to_datetime(m["eff_date"]).dt.normalize(),
              "y":y,"p_raw":oof}).to_parquet("reports/checks/meta_y_2x_oof.parquet",index=False)
print({"rows":len(y),"pos":int((y==1).sum()),"pmax":float(oof.max())})
