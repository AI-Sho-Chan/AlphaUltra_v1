import os, json
EXP=os.environ["EXP_DIR"]; meta=json.loads(open(os.path.join(EXP,"meta_monthly_ci_v2.json"),encoding="utf-8").read())
cands=[]
for k,v in meta.items():
    if k in ("thr","H"): continue
    if isinstance(v,dict) and "ci" in v:
        lo,hi = v["ci"][0], v["ci"][1]
        cands.append({"rule":k,"n":v["n"],"ann":v["ann"],"lo":lo,"hi":hi})
if not cands:
    pick={"rule":"none"}
else:
    pos=[r for r in cands if r["lo"]>0]
    pick = sorted(pos, key=lambda r:(-r["ann"],-r["n"]))[0] if pos else sorted(cands, key=lambda r:r["hi"], reverse=True)[0]
open(os.path.join(EXP,"pick_meta.json"),"w",encoding="utf-8").write(json.dumps(pick,ensure_ascii=False,indent=2))
print(pick)
