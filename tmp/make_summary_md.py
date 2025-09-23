import os, json
EXP=os.environ["EXP_DIR"]
evt=json.loads(open(os.path.join(EXP,"evt_cost_ci_v2.csv")).read().splitlines()[0] if False else "[]")
meta=json.loads(open(os.path.join(EXP,"meta_monthly_ci_v2.json"),encoding="utf-8").read())
fnd =json.loads(open(os.path.join(EXP,"fnd_best.json"),encoding="utf-8").read())
open(os.path.join(EXP,"SUMMARY.md"),"w",encoding="utf-8").write(
f"""# Hardcheck Summary ({EXP})
- EVT cost-adjusted CI: see `evt_cost_ci_v2.csv` (CI_lo>0 行が有意)
- META monthly CI: {meta}
- FND best (PPV>=0.7 最大coverage): {fnd}
""")
print({"summary":os.path.join(EXP,"SUMMARY.md")})
