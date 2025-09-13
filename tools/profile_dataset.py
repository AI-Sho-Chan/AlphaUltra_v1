import argparse, pathlib, pandas as pd
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--dataset", default="yahoo_default")
    ap.add_argument("--out", default="reports/profile/yahoo_default_profile.md")
    args=ap.parse_args()
    f=pathlib.Path(f"data/gold/{args.dataset}/features.parquet")
    l=pathlib.Path(f"data/gold/{args.dataset}/labels.parquet")
    out=pathlib.Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    md=[]
    if not f.exists() or not l.exists():
        md+=["# Dataset Profile","- status: MISSING gold parquet"]
        out.write_text("\n".join(md), encoding="utf-8"); print(f"[profile] {out}"); return
    df=pd.read_parquet(f); lb=pd.read_parquet(l)
    md+=["# Dataset Profile",f"- dataset: {args.dataset}",f"- features: {f}",f"- labels: {l}"]
    md+=[f"- rows(features): {len(df):,}", f"- cols(features): {len(df.columns)}"]
    if "date" in df.columns:
        md+=[f"- date range: {df['date'].min()} .. {df['date'].max()}"]
    if "ticker" in df.columns:
        md+=[f"- tickers: {df['ticker'].nunique():,}"]
    md+=["## columns (features)",", ".join(df.columns)]
    na = df.isna().mean().sort_values(ascending=False).head(20)
    md+=["## top20 missing ratio","| col | missing_ratio |","|---|---:|"]
    for k,v in na.items(): md+= [f"| {k} | {v:.4f} |"]
    out.write_text("\n".join(md), encoding="utf-8")
    print(f"[profile] {out}")
if __name__=="__main__":
    main()
