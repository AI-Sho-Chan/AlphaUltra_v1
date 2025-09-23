import os, json, numpy as np, pandas as pd
EXP = os.environ["EXP_DIR"]
o = pd.read_parquet(r"reports/checks/fnd_y_2x_oof.parquet")[["p_raw","y"]].sort_values("p_raw",ascending=False)
best=None
for a in np.linspace(0.01,0.30,30):
    k=max(1,int(len(o)*a)); sel=o.head(k); ppv=float(sel["y"].mean()) if k>0 else 0.0
    if ppv>=0.7: best={"alpha":float(a),"k":int(k),"ppv":ppv}; break
with open(os.path.join(EXP,"fnd_summary.json"),"w",encoding="utf-8") as f: json.dump(best or {"alpha":"none"},f,ensure_ascii=False,indent=2)
print({"fnd_done":True,"out":os.path.join(EXP,"fnd_summary.json")})
