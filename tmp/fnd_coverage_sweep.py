import os, json, numpy as np, pandas as pd
EXP=os.environ["EXP_DIR"]
o=pd.read_parquet(r"reports/checks/fnd_y_2x_oof.parquet")[["p_raw","y"]].sort_values("p_raw",ascending=False)
rows=[]
for a in np.linspace(0.01,0.30,30):
    k=max(1,int(len(o)*a)); sel=o.head(k)
    rows.append({"alpha":float(a),"k":int(k),"ppv":float(sel["y"].mean()),"coverage":float(a)})
df=pd.DataFrame(rows)
df.to_csv(os.path.join(EXP,"fnd_ppv_coverage_sweep.csv"), index=False)
best=df[df["ppv"]>=0.7].sort_values(["coverage","ppv"],ascending=[False,False]).head(1)
json.dump((best.to_dict(orient="records")[0] if len(best)>0 else {"alpha":"none"}),
          open(os.path.join(EXP,"fnd_best_wide.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=2)
print({"fnd_sweep":os.path.join(EXP,"fnd_ppv_coverage_sweep.csv")})
