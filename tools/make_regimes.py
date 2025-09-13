import argparse, pandas as pd, numpy as np, pathlib

ROOT = pathlib.Path("C:/AI/AlphaUltra")


def label_regime(df, vol_win=60, trend_win=100, vol_q=0.7, trend_thr=0.0):
    df = df.copy()
    df["ret"] = df["close"].pct_change()
    df["vol"] = df["ret"].rolling(vol_win).std()
    df["ma_fast"] = df["close"].rolling(20).mean()
    df["ma_slow"] = df["close"].rolling(trend_win).mean()
    df["trend"] = (df["ma_fast"] - df["ma_slow"]) / df["ma_slow"]
    vol_hi = df["vol"].quantile(vol_q)
    cond_bull = df["trend"] > trend_thr
    cond_bear = df["trend"] <= trend_thr
    cond_high = df["vol"] >= vol_hi
    cond_low  = df["vol"] <  vol_hi
    reg = np.select(
        [cond_bull & cond_low, cond_bull & cond_high, cond_bear & cond_low, cond_bear & cond_high],
        ["bull_lowvol","bull_highvol","bear_lowvol","bear_highvol"],
        default="unknown"
    )
    out = df[["date"]].copy()
    out["regime"] = reg
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in_csv", default=str(ROOT/"data/aux/index_timeseries.csv"))
    ap.add_argument("--out_csv", default=str(ROOT/"data/aux/regimes.csv"))
    ap.add_argument("--vol_win", type=int, default=60)
    ap.add_argument("--trend_win", type=int, default=100)
    ap.add_argument("--vol_q", type=float, default=0.7)
    ap.add_argument("--trend_thr", type=float, default=0.0)
    args = ap.parse_args()

    IN = pathlib.Path(args.in_csv)
    OUT = pathlib.Path(args.out_csv)
    OUT.parent.mkdir(parents=True, exist_ok=True)

    if not IN.exists():
        dates = pd.bdate_range("2015-01-01", periods=252*5)
        price = 100*np.exp(np.cumsum(np.random.normal(0,0.01,size=len(dates))))
        df = pd.DataFrame({"date": dates, "close": price})
    else:
        df = pd.read_csv(IN)
        if "date" not in df.columns or "close" not in df.columns:
            raise ValueError("index_timeseries.csv must have columns: date, close")
    df["date"] = pd.to_datetime(df["date"]) 
    df = df.sort_values("date").reset_index(drop=True)

    out = label_regime(df, args.vol_win, args.trend_win, args.vol_q, args.trend_thr)
    out.to_csv(OUT, index=False)
    print(f"[regimes] wrote {OUT}")


if __name__ == "__main__":
    main()

