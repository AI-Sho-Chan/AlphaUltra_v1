import json, os, pandas as pd
PICK=r"C:\AI\AlphaUltra_v1_clean\reports\exp\20250923_202008\pick_evt.json"
thr, H = 0.205, 60
N = int(json.loads(open(PICK,encoding="utf-8").read())["N"]) if os.path.exists(PICK) else 10
px = pd.read_parquet(r"data/proc/prices/jp_prices_std_compat_q4p.parquet",
                     columns=["ticker","eff_date","adj_close"]).sort_values(["ticker","eff_date"])
o  = pd.read_parquet(r"reports/checks/tdnet_model_y_2x_oof.parquet")[["ticker","eff_date","p_raw"]]
days = sorted(px["eff_date"].unique())[-40:]  # バッファ広め→後で20日に切る
out_dir = r"reports/daily"; os.makedirs(out_dir, exist_ok=True)
made = []
for d in days[::-1][:20]:  # 直近20営業日を新しい順
    cand = o[o["eff_date"]==d].sort_values("p_raw",ascending=False)
    cand = cand[cand["p_raw"]>=thr].head(N).copy()
    if cand.empty: continue
    cand["entry"]=pd.to_datetime(d)
    cand["exit"]=pd.to_datetime(d)+pd.tseries.offsets.BDay(H)
    fn = os.path.join(out_dir, f"evt_candidates_{str(pd.to_datetime(d).date())}.csv")
    cand.to_csv(fn, index=False); made.append(fn)
print({"made":len(made),"files":made[:3]})
