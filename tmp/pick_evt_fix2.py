import os, json, pandas as pd
EXP=os.environ["EXP_DIR"]
df=pd.read_csv(os.path.join(EXP,"evt_cost_ci_v2.csv"))
# 期待列: N,bps,n,ann,ci_lo,ci_hi
need={"N","bps","n","ann","ci_lo","ci_hi"}
missing=need-set(df.columns)
if missing: raise SystemExit({"error":"columns missing", "missing":list(missing), "have":list(df.columns)})
sig=df[df["ci_lo"]>0].copy()
best = sig.sort_values(["bps","N","ci_hi"], ascending=[True,True,False]).head(1)
if best.empty: best = df.sort_values(["ci_hi"], ascending=False).head(1)
out=best.to_dict(orient="records")[0]
open(os.path.join(EXP,"pick_evt.json"),"w",encoding="utf-8").write(json.dumps(out,ensure_ascii=False,indent=2))
print(out)
