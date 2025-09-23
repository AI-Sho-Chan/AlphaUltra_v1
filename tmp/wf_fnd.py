import pandas as pd, numpy as np, json, pathlib
OOF = "reports/checks/fnd_y_2x_oof.parquet"
o = pd.read_parquet(OOF)[["ticker","eff_date","p_raw","y"]].sort_values("p_raw", ascending=False)
# 上位αを走査しPPV>=0.7の最小αを採用
best=None
for a in np.linspace(0.01, 0.30, 30):
    k = max(1, int(len(o)*a))
    sel = o.head(k)
    ppv = sel["y"].mean() if k>0 else 0
    if ppv>=0.7:
        best={"alpha":float(a),"k":int(k),"ppv":float(ppv)}
        break
pathlib.Path(r"$exp\fnd_summary.json").write_text(json.dumps(best or {"alpha":"none"}, indent=2, ensure_ascii=False), encoding="utf-8")
print({"fnd_done":True,"file":"$exp\\fnd_summary.json"})
