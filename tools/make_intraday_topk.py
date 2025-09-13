import argparse, pathlib, pandas as pd, numpy as np, datetime as dt

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=50)
    ap.add_argument("--date", type=str, default=None)          # YYYY-MM-DD
    ap.add_argument("--type", choices=["gate","sgn"], default="gate")
    ap.add_argument("--gate", type=float, default=5.0)
    ap.add_argument("--sgn",  type=float, default=10.0)
    ap.add_argument("--root", type=str, default="C:/AI/AlphaUltra")
    args = ap.parse_args()

    root = pathlib.Path(args.root)
    feat_p = root/"data/gold/yahoo_default/features_events.parquet"
    df = pd.read_parquet(feat_p)
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()

    d = pd.to_datetime(args.date).normalize() if args.date else df["date"].max()
    day = df.loc[df["date"]==d].copy()
    for col in ("event_strength","event_signal","ret5","ret20"):
        if col not in day.columns: day[col]=0.0

    if args.type=="gate":
        score = (day["ret20"] - day["ret5"]) * (1.0 + args.gate*day["event_strength"])
        tag = f"GATE{args.gate:g}"
    else:
        score = (day["ret20"] - day["ret5"]) * (1.0 + args.sgn*day["event_signal"])
        tag = f"SGN{args.sgn:g}"

    day["score"] = score.replace([np.inf,-np.inf], np.nan).fillna(0.0)
    top = day.sort_values("score", ascending=False).head(args.k).copy()

    out_dir = root/"reports/intraday"; out_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_p = out_dir/f"topk_{tag}_{stamp}.csv"
    md_p  = out_dir/f"topk_{tag}_{stamp}.md"
    latest = out_dir/"latest_topk.csv"

    prev = []
    if latest.exists():
        try:
            prev = pd.read_csv(latest)["ticker"].astype(str).tolist()
        except Exception:
            prev = []

    cur = top["ticker"].astype(str).tolist()
    new  = [t for t in cur if t not in prev]
    gone = [t for t in prev if t not in cur]

    top.to_csv(csv_p, index=False)
    top[["ticker","score"]].to_csv(latest, index=False)

    cov_all = float((day.get("event_strength",0)>0).mean()) if "event_strength" in day else 0.0
    cov_top = float((top.get("event_strength",0)>0).mean()) if "event_strength" in top else 0.0

    md = []
    md.append(f"# Intraday TopK ({tag}) {stamp}")
    md.append("")
    md.append(f"- date: {d.date()}  k: {args.k}")
    md.append(f"- coverage (all/topK): {cov_all:.3f} / {cov_top:.3f}")
    md.append(f"- delta: +{len(new)} / -{len(gone)}  new: {', '.join(new[:15])}")
    md.append("")
    md.append("|rank|ticker|score|event_strength|event_signal|")
    md.append("|---:|---|---:|---:|---:|")
    for i,row in enumerate(top.itertuples(index=False),1):
        md.append(f"|{i}|{row.ticker}|{getattr(row,'score',0.0):.6f}|{getattr(row,'event_strength',0.0):.3f}|{getattr(row,'event_signal',0.0):.3f}|")
    md_p.write_text("\n".join(md), encoding="utf-8")

    print(f"[TOPK] {csv_p}  delta +{len(new)} -{len(gone)}  new={new[:5]}")
if __name__ == "__main__":
    main()