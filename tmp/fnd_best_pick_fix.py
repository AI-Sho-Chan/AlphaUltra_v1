import os, pandas as pd, json
EXP=os.environ["EXP_DIR"]; path=os.path.join(EXP,"fnd_ppv_curve.csv")
df=pd.read_csv(path)
cand=df[df["ppv"]>=0.7].sort_values(["coverage","ppv"],ascending=[False,False]).head(1)
best=cand.to_dict(orient="records")[0] if len(cand)>0 else {"alpha":"none"}
with open(os.path.join(EXP,"fnd_best.json"),"w",encoding="utf-8") as f: json.dump(best, f, ensure_ascii=False, indent=2)
print(best)
