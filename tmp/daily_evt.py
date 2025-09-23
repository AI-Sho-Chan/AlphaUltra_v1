import json, os, pandas as pd, numpy as np, datetime as dt
PICK=os.path.join(r"reports\exp\20250923_202008","pick_evt.json")
thr=0.205; H=60
pick=json.loads(open(PICK,encoding="utf-8").read()); N=int(pick["N"])
px=pd.read_parquet(r"data/proc/prices/jp_prices_std_compat_q4p.parquet",
                   columns=["ticker","eff_date","adj_close"]).sort_values(["ticker","eff_date"])
o =pd.read_parquet(r"reports/checks/tdnet_model_y_2x_oof.parquet")[["ticker","eff_date","p_raw"]]
today = px["eff_date"].max()
cand = o[o["eff_date"]==today].sort_values("p_raw",ascending=False)
cand = cand[cand["p_raw"]>=thr].head(N).copy()
cand["entry"]=today; cand["exit"]=pd.to_datetime(today)+pd.tseries.offsets.BDay(H)
out_dir=r"reports\daily"; os.makedirs(out_dir, exist_ok=True)
fn=os.path.join(out_dir,f"evt_candidates_{today.date()}.csv")
cand.to_csv(fn, index=False)
print({"daily_evt":fn,"rows":len(cand),"H":H,"thr":thr,"N":N})
