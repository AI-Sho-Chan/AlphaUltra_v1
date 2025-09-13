import argparse, pathlib, pandas as pd, numpy as np
from datetime import datetime

def pick_ticker_col(df):
    for c in ["ticker","symbol","code","Code","銘柄コード"]:
        if c in df.columns: return c
    return df.columns[0]

def read_tickers_csv(p):
    df = pd.read_csv(p)
    c = pick_ticker_col(df)
    return set(df[c].astype(str))

def jaccard(a,b):
    u = len(a|b)
    return (len(a&b)/u) if u>0 else np.nan

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    ap.add_argument("--topk_dir", default="reports/intraday")
    ap.add_argument("--features", default="data/gold/yahoo_default/features_events.parquet")
    ap.add_argument("--events_dir", default="data/gold/events")
    ap.add_argument("--out_md", default=None)
    ap.add_argument("--out_csv", default=None)
    args = ap.parse_args()

    topk_dir = pathlib.Path(args.topk_dir)
    topk_dir.mkdir(parents=True, exist_ok=True)
    date_str = args.date.replace("-","")

    # 調査対象のTopKスナップショット（当日分）
    snaps = sorted(topk_dir.glob(f"topk_*_{date_str}_*.csv"), key=lambda x: x.stat().st_mtime)
    if len(snaps)==0:
        print("[KPI] no topk snapshots for", args.date)
        snaps = []

    # 直近N（最大8）で安定度を測る
    N = 8
    snaps = snaps[-N:]
    tickers_list = [read_tickers_csv(p) for p in snaps]
    jac = []
    for i in range(1,len(tickers_list)):
        jac.append(jaccard(tickers_list[i-1], tickers_list[i]))
    mean_jac = float(np.nanmean(jac)) if len(jac)>0 else np.nan

    # 直近スナップショットのTopK
    last_topk = tickers_list[-1] if len(tickers_list)>0 else set()
    K = len(last_topk)

    # 当日イベントの “強イベント” カバレッジ（features_events.parquet に依存）
    cov = np.nan
    ev_cnt = tick_cnt = 0
    features_pq = pathlib.Path(args.features)
    if features_pq.exists() and K>0:
        df = pd.read_parquet(features_pq, columns=["date","ticker","event_strength"])
        df["date"] = pd.to_datetime(df["date"]).dt.normalize()
        d = pd.to_datetime(args.date)
        sub = df[df["date"]==d]
        if "event_strength" in sub.columns and len(sub)>0:
            strong = sub[sub["event_strength"]>0]
            elig = set(strong["ticker"].astype(str))
            ev_cnt = int(len(sub))
            tick_cnt = int(strong["ticker"].nunique())
            cov = (len(last_topk & elig)/len(elig)) if len(elig)>0 else np.nan

    # 当日のTDNETイベント件数（参考）
    evp = pathlib.Path(args.events_dir)/f"tdnet_events_{date_str}.parquet"
    tdnet_rows = None
    if evp.exists():
        try:
            td = pd.read_parquet(evp, columns=["ticker"])
            tdnet_rows = int(len(td))
        except Exception:
            pass

    # 出力
    row = {
        "date": args.date,
        "snapshots": len(snaps),
        "K": K,
        "mean_jaccard": None if np.isnan(mean_jac) else round(mean_jac,4),
        "coverage_vs_strong_events": None if (isinstance(cov,float) and np.isnan(cov)) else round(cov,4),
        "features_rows_today": ev_cnt,
        "strong_ticker_cnt": tick_cnt,
        "tdnet_rows_today": tdnet_rows,
    }
    md = (
        f"# Intraday KPI {args.date}\n\n"
        f"- snapshots: {row['snapshots']}\n"
        f"- K(last): {row['K']}\n"
        f"- TopK stability (mean Jaccard): {row['mean_jaccard']}\n"
        f"- Coverage vs strong events: {row['coverage_vs_strong_events']}\n"
        f"- features_rows_today: {row['features_rows_today']}\n"
        f"- strong_ticker_cnt: {row['strong_ticker_cnt']}\n"
        f"- tdnet_rows_today: {row['tdnet_rows_today']}\n"
    )
    csv_line = ",".join(str(row[k]) for k in ["date","snapshots","K","mean_jaccard","coverage_vs_strong_events","features_rows_today","strong_ticker_cnt","tdnet_rows_today"])+"\n"

    if args.out_md:
        pathlib.Path(args.out_md).parent.mkdir(parents=True, exist_ok=True)
        with open(args.out_md,"w",encoding="utf-8") as f: f.write(md)
    if args.out_csv:
        pathlib.Path(args.out_csv).parent.mkdir(parents=True, exist_ok=True)
        hdr = "date,snapshots,K,mean_jaccard,coverage_vs_strong_events,features_rows_today,strong_ticker_cnt,tdnet_rows_today\n"
        p = pathlib.Path(args.out_csv)
        if not p.exists():
            with open(p,"w",encoding="utf-8") as f: f.write(hdr)
        with open(p,"a",encoding="utf-8") as f: f.write(csv_line)

    print(md.strip())

if __name__=="__main__":
    main()