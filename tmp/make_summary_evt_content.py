import os, json, datetime
EXP=os.environ["EXP_DIR"]
res=json.loads(open(os.path.join(EXP,"evt_typeXcontent_ci.json"),encoding="utf-8").read())

def pick(sig):
    ans=[]
    for k,v in sig.items():
        if v.get("ci",[0,0])[0]>0 and v.get("p_holm",1.0)<0.05:
            ans.append({"key":k,"n":v["n"],"ann":round(v["ann"],2),
                        "lo":round(v["ci"][0],2),"hi":round(v["ci"][1],2),
                        "p_holm":round(v["p_holm"],4)})
    return sorted(ans, key=lambda x:(-x["ann"], -x["n"]))[:10]

H20 = pick(res.get("H20_typeXcontent",{}))
H60 = pick(res.get("H60_typeXcontent",{}))

def lines_for(tag, rows):
    L=[f"## {tag} 有意（上位）"]
    if rows:
        for r in rows: L.append(f"- {r}")
    else:
        L.append("- none")
    return L

ts=datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
lines=[f"# EVT type × content ({EXP})",""]
lines += lines_for("H=20", H20); lines.append("")
lines += lines_for("H=60", H60)

open(os.path.join(EXP,"SUMMARY_EVT_CONTENT.md"),"w",encoding="utf-8").write("\n".join(lines))
print({"summary":os.path.join(EXP,"SUMMARY_EVT_CONTENT.md")})
