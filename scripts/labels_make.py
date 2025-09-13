import argparse, pandas as pd, numpy as np
from pathlib import Path
import yaml
def fwd_max_ratio(closes, h=252):
    v=closes.values.astype("float64")
    n=len(v); out=np.full(n, np.nan)
    for i in range(n):
        j=min(n, i+h+1)
        mx=v[i+1:j].max() if i+1<j else v[i]
        out[i]= mx/ v[i] if v[i]>0 else np.nan
    return out
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--config",default="configs/tdnet_model.yaml")
    args=ap.parse_args()
    cfg=yaml.safe_load(open(args.config,"r",encoding="utf-8")) or {}
    panel=Path(cfg["paths"]["dataset_root"])/"tdnet_panel.parquet"
    labels_root=Path(cfg["paths"]["labels_root"]); labels_root.mkdir(parents=True,exist_ok=True)
    h=int(cfg["labels"]["y2x"]["horizon_days"]); ratio=float(cfg["labels"]["y2x"]["ratio"])
    df=pd.read_parquet(panel)
    out=[]
    for t,g in df.groupby("ticker"):
        g=g.sort_values("date").copy()
        g["y_2x"]= (fwd_max_ratio(g["adj_close"], h) >= ratio).astype("int8")
        out.append(g[["ticker","date","y_2x"]])
    lab=pd.concat(out, ignore_index=True)
    lab.to_parquet(labels_root/"targets.parquet", index=False)
    print(f"[INFO] labels rows={len(lab)} -> {labels_root/'targets.parquet'}")
if __name__=="__main__": main()
