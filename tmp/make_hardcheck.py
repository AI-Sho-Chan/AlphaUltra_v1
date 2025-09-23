import os, json, pandas as pd
EXP=os.environ["EXP_DIR"]
evt=json.loads(open(os.path.join(EXP,"evt_significant.json"),encoding="utf-8").read())
meta=json.loads(open(os.path.join(EXP,"meta_monthly_ci.json"),encoding="utf-8").read())
fnd =json.loads(open(os.path.join(EXP,"fnd_best.json"),encoding="utf-8").read())
rep={"EVT_significant":evt.get("evt_significant_rows",[]),"META_monthly_CI":meta,"FND_best":fnd}
open(os.path.join(EXP,"summary_hardcheck.json"),"w",encoding="utf-8").write(json.dumps(rep,ensure_ascii=False,indent=2))
print({"hardcheck":os.path.join(EXP,"summary_hardcheck.json")})
