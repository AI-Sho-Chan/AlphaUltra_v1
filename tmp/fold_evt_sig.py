import os, pandas as pd, json
EXP=os.environ["EXP_DIR"]
df=pd.read_csv(os.path.join(EXP,"evt_cost_ci.csv"), index_col=0)
def ok(row): 
    try: 
        lo=float(eval(row["ci"])[0]); 
        return lo>0 
    except Exception: 
        return False
sig=df[df.apply(ok,axis=1)]
out={"evt_significant_rows": sig.reset_index().to_dict(orient="records")}
open(os.path.join(EXP,"evt_significant.json"),"w",encoding="utf-8").write(json.dumps(out,ensure_ascii=False,indent=2))
print({"N":int(sig.shape[0]),"file":os.path.join(EXP,"evt_significant.json")})
