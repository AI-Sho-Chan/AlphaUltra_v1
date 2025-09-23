import os, json, ast, pandas as pd
EXP=os.environ["EXP_DIR"]; df=pd.read_csv(os.path.join(EXP,"evt_cost_ci_v2.csv"))
def ci_lo(x):
    try: return float(x.split(",")[0].split("[")[-1])
    except: return -1e9
def ci_hi(x):
    try: return float(x.split(",")[1].split("]")[0])
    except: return -1e9
df["ci_lo"]=df["ci"].apply(ci_lo); df["ci_hi"]=df["ci"].apply(ci_hi)
sig=df[df["ci_lo"]>0]
best = sig.sort_values(["bps","N","ci_hi"], ascending=[True,True,False]).head(1)
if best.empty: best = df.sort_values(["ci_hi"], ascending=False).head(1)
out = best.to_dict(orient="records")[0]
open(os.path.join(EXP,"pick_evt.json"),"w",encoding="utf-8").write(json.dumps(out,ensure_ascii=False,indent=2))
print(out)
