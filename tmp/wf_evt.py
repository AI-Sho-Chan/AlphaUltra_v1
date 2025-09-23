import pandas as pd, numpy as np, json, pathlib, itertools, math
from scipy import stats

OOF = "reports/checks/tdnet_model_y_2x_oof.parquet"
PRC = "data/proc/prices/jp_prices_std_compat_q4p.parquet"
thr = 0.205
Hs  = [5,20,60]
Ns  = [5,10,20]

o = pd.read_parquet(OOF)[["ticker","eff_date","p_raw"]]
p = pd.read_parquet(PRC, columns=["ticker","eff_date","adj_close"]).sort_values(["ticker","eff_date"])
p["next_ret"] = p.groupby("ticker")["adj_close"].pct_change().shift(-1)  # 1日先の場当たり

# H日合成リターン（単利近似）：連続加算で近似
def h_ret(df, H):
    g = df.groupby("ticker", group_keys=False)
    r = g["next_ret"].apply(lambda s: s.rolling(H, min_periods=H).sum()).shift(-(H-1))
    return df.assign(**{f"ret_H{H}": r})

res = {}
for H in Hs:
    ph = h_ret(p.copy(), H).dropna(subset=[f"ret_H{H}"])
    sig = o.merge(ph[["ticker","eff_date",f"ret_H{H}"]], on=["ticker","eff_date"], how="inner")
    sig["pick"] = (sig["p_raw"] >= thr).astype(int)
    # 時系列でN制約：日毎に上位p_rawからN件を採用
    sig = sig.sort_values(["eff_date","p_raw"], ascending=[True,False])
    sig["rank"] = sig.groupby("eff_date")["p_raw"].rank(method="first", ascending=False)
    out_rows=[]
    for N in Ns:
        pick = sig[(sig["pick"]==1) & (sig["rank"]<=N)].copy()
        if pick.empty:
            res[(H,N)]={"coverage":0,"ann_excess":0,"t_p":1.0}
            continue
        # ポートの日次P/L：同日採用を均等重み
        day = pick.groupby("eff_date")[f"ret_H{H}"].mean().rename("pl")
        # 基本統計
        mu = day.mean(); sd = day.std(ddof=1); n=len(day)
        ann_excess = mu * (252/H)  # 粗い年率換算
        t_p = stats.ttest_1samp(day, 0.0, alternative="greater").pvalue if sd>0 and n>1 else 1.0
        res[(H,N)] = {"coverage": float(len(pick)/len(sig)), "ann_excess": float(ann_excess), "t_p": float(t_p), "n_trades": int(len(pick))}
# 保存
pathlib.Path(r"$exp\evt_summary.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
print({"evt_done":True,"file":"$exp\\evt_summary.json"})
