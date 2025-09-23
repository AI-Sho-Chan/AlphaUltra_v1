import os, json
EXP=os.environ["EXP_DIR"]
pick_evt=json.loads(open(os.path.join(EXP,"pick_evt.json"),encoding="utf-8").read()) if os.path.exists(os.path.join(EXP,"pick_evt.json")) else {}
pick_meta=json.loads(open(os.path.join(EXP,"pick_meta.json"),encoding="utf-8").read()) if os.path.exists(os.path.join(EXP,"pick_meta.json")) else {}
fnd_best=json.loads(open(os.path.join(EXP,"fnd_best.json"),encoding="utf-8").read()) if os.path.exists(os.path.join(EXP,"fnd_best.json")) else {}
conf={"EVT":{"H":60,"thr":0.205,"N":pick_evt.get("N",10),"bps":pick_evt.get("bps",10)},
      "FND":{"alpha":fnd_best.get("alpha",0.10),"coverage":fnd_best.get("coverage",0.10)},
      "META":{"rule":pick_meta.get("rule","A_thr")}}
open(os.path.join(EXP,"ops_params.json"),"w",encoding="utf-8").write(json.dumps(conf,ensure_ascii=False,indent=2))
print(conf)
