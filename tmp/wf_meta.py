import pandas as pd, numpy as np, json, pathlib
from scipy import stats
OOF = "reports/checks/meta_y_2x_oof.parquet"
PRC = "data/proc/prices/jp_prices_std_compat_q4p.parquet"
thr = 0.355
H   = 20
m = pd.read_parquet(OOF)[["ticker","eff_date","p_raw"]]
p = pd.read_parquet(PRC, columns=["ticker","eff_date","adj_close"]).sort_values(["ticker","eff_date"])
p["next_ret"] = p.groupby("ticker")["adj_close"].pct_change().shift(-1)
# H日近似
def h_ret(df, H):
    g = df.groupby("ticker", group_keys=False)
    r = g["next_ret"].apply(lambda s: s.rolling(H, min_periods=H).sum()).shift(-(H-1))
    return df.assign(ret=r)
ph = h_ret(p.copy(), H).dropna(subset=["ret"])
sig = m.merge(ph[["ticker","eff_date","ret"]], on=["ticker","eff_date"], how="inner")
sig = sig[sig["p_raw"]>=thr]
day = sig.groupby("eff_date")["ret"].mean()
ann_excess = day.mean()*(252/H)
pval = stats.ttest_1samp(day, 0.0, alternative="greater").pvalue if len(day)>2 else 1.0
out = {"H":H,"thr":thr,"ann_excess":float(ann_excess),"t_p":float(pval),"coverage": float(len(sig)/len(m))}
pathlib.Path(r"$exp\meta_summary.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
print({"meta_done":True,"file":"$exp\\meta_summary.json"})
