import argparse, pathlib, pandas as pd
from datetime import datetime, timezone
import json

ROOT = pathlib.Path(r"C:\AI\AlphaUltra")
GOLD = ROOT/"data/gold/yh_intraday"
LIVE = ROOT/"reports/live"
STATE= ROOT/"data/live"

def score_mom(df):
    s = df[["ticker","date","ret1","ret5"]].dropna().copy()
    s["score"] = s["ret1"] + 0.5*s["ret5"]
    return s

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=30)
    ap.add_argument("--since_min", type=int, default=120)
    args = ap.parse_args()

    f = GOLD/"features.parquet"
    if not f.exists():
        print("[rt-score] no features yet"); return
    df = pd.read_parquet(f)
    df = df.sort_values("date")
    # 直近N分
    try:
        cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(minutes=args.since_min)
        df_recent = df[df["date"] >= cutoff.tz_localize(None)]
    except Exception:
        df_recent = df.tail(5000)

    s = score_mom(df_recent)
    last = s.sort_values(["date"]).groupby("ticker").tail(1)
    top = last.sort_values("score", ascending=False).head(args.k)

    LIVE.mkdir(parents=True, exist_ok=True)
    STATE.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)
    ts  = now.strftime("%Y-%m-%d_%H%M%S")
    md  = LIVE/f"alerts_{ts}Z.md"
    latest = LIVE/"alerts_latest.md"
    js  = STATE/"last_top_k.json"

    cols = ["ticker","date","score","ret1","ret5"]
    lines = ["# Live Alerts (MOM)", f"- generated_utc: {now.isoformat()}"]
    if top.empty:
        lines += ["_no signals_"]
        top_list=[]
    else:
        lines += ["","| " + " | ".join(cols) + " |","|" + "|".join(["---"]*len(cols)) + "|"]
        for _,r in top.iterrows():
            lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
        top_list = top["ticker"].astype(str).tolist()

    md.write_text("\n".join(lines), encoding="utf-8")
    latest.write_text("\n".join(lines), encoding="utf-8")
    js.write_text(json.dumps({"utc":now.isoformat(),"tickers":top_list}, ensure_ascii=False), encoding="utf-8")
    print(f"[alerts] wrote {md} and {latest}")
if __name__ == "__main__":
    main()
