import pandas as pd, json, pathlib
o = pd.read_parquet(r"reports/checks/tdnet_model_y_2x_oof.parquet")
print({"rows":len(o),"pos":int((o["y"]==1).sum()),
       "p_min":float(o["p_raw"].min()),"p_max":float(o["p_raw"].max())})
p = pathlib.Path("reports/calibrate_isotonic_v2.json")
print("calib_exists:", p.exists())
if p.exists(): print(p.read_text(encoding="utf-8"))
