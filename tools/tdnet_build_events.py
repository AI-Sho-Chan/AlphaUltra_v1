import argparse, pathlib, json, pandas as pd, numpy as np
ROOT=pathlib.Path(r"C:\AI\AlphaUltra")
EV  = ROOT/"data/gold/events"
CAL = EV/"calibration.json"

def novelty(title:str)->float:
    L=len(title or ""); return float(np.tanh(L/80))

def size_feature(row)->float:
    h=((row.get("headline") or "")+" "+(row.get("title_html") or "")).replace("　"," ")
    s=0.0
    for kw,w in [("自社株買",0.8),("自己株式の取得",0.8),("公募増資",-0.8),("希薄化",-0.7),
                 ("配当予想の上方修正",0.6),("下方修正",-0.6)]:
        if kw in h: s+=w
    return float(s)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--in-parquet", required=True)
    ap.add_argument("--out-parquet", default=str(EV/"tdnet_events.parquet"))
    args=ap.parse_args()
    import pathlib, sys; p=pathlib.Path(args.in_parquet)
if not p.exists(): print(f"[events] missing {p}"); sys.exit(0)
df=pd.read_parquet(args.in_parquet)
    if df.empty: 
        print("[events] empty input"); return
    out=pd.DataFrame()
    out["ticker"]=df["ticker"].astype(str)
    out["event_time"]=pd.to_datetime(df["published_at"])
    out["source"]="TDNET"
    out["category"]=df["category"].astype(str)
    out["headline"]=df["headline"].astype(str)
    out["url"]=df["url"].astype(str)
    out["novelty"]=df["title_html"].astype(str).map(novelty)
    out["size_raw"]=df.apply(size_feature, axis=1)
    out["is_validated"]=False
    if CAL.exists():
        try:
            cal=json.loads(CAL.read_text(encoding="utf-8"))
            wn=cal.get("w_novelty",0.3); ws=cal.get("w_size",0.7); b=cal.get("bias",0.0)
            out["event_score"]=out["novelty"]*wn + out["size_raw"]*ws + b
            out["is_validated"]=True
        except Exception:
            pass
    EV.mkdir(parents=True, exist_ok=True); out.to_parquet(args.out_parquet, index=False)
    print("[events] ->", args.out_parquet, "rows=", len(out))
if __name__=="__main__": main()

