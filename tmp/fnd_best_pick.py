import os, json, numpy as np, pandas as pd
EXP=os.environ["EXP_DIR"]; path=os.path.join(EXP,"fnd_ppv_curve.csv")
df=pd.read_csv(path)
cand=df[df["ppv"]>=0.7].sort_values(["coverage","ppv"],ascending=[False,False]).head(1)
best=cand.to_dict(orient="records")[0] if len(cand)>0 else {"alpha":"none"}
pd.Series(best).to_json(os.path.join(EXP,"fnd_best.json"), force_ascii=False, indent=2)
print({"fnd_best":os.path.join(EXP,"fnd_best.json")})
