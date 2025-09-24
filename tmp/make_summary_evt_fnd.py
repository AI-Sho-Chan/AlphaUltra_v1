import os, json, datetime
EXP=os.environ["EXP_DIR"]
evt=json.loads(open(os.path.join(EXP,"evt_by_type_ci.json"),encoding="utf-8").read())
fnd=json.loads(open(os.path.join(EXP,"fnd_best_wide.json"),encoding="utf-8").read())
ts=datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
lines=[f"# Hardcheck Summary ({EXP})","",
       "## EVT by type (CI_lo>0 かつ p_holm<0.05 が“有意”)",
       f"- H=20 keys: {list(evt.get('H20_event_type',{}).keys())[:6]} ...",
       f"- H=60 keys: {list(evt.get('H60_event_type',{}).keys())[:6]} ...",
       "",
       "## FND sweep (PPV>=0.7 最大coverage)",
       f"- best: {fnd}",
       ""]
open(os.path.join(EXP,"SUMMARY.md"),"w",encoding="utf-8").write("\n".join(lines))
print({"summary":os.path.join(EXP,"SUMMARY.md")})
