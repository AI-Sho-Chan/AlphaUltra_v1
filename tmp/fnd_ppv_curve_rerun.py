import os, numpy as np, pandas as pd, pathlib
EXP=os.environ["EXP_DIR"]
o=pd.read_parquet(r"reports/checks/fnd_y_2x_oof.parquet")[["p_raw","y"]].sort_values("p_raw",ascending=False)
rows=[]
for a in np.linspace(0.01,0.10,10):
    k=max(1,int(len(o)*a)); sel=o.head(k)
    rows.append({"alpha":float(a),"k":int(k),"ppv":float(sel["y"].mean()),"coverage":float(a)})
pathlib.Path(EXP).mkdir(parents=True, exist_ok=True)
pd.DataFrame(rows).to_csv(os.path.join(EXP,"fnd_ppv_curve.csv"), index=False)
print({"fnd_curve":os.path.join(EXP,"fnd_ppv_curve.csv")})
