import pandas as pd
from pathlib import Path

LABEL_COLS = ["y_2x","rel_1M","rel_3M","rel_12M"]

def main():
    ds_p = Path("data/proc/dataset/dataset_text_only.parquet")
    y_p  = Path("data/proc/labels/targets.parquet")
    out  = Path("data/proc/dataset/dataset_final.parquet")
    out.parent.mkdir(parents=True, exist_ok=True)
    if not ds_p.exists() or not y_p.exists():
        print(f"missing inputs ds={ds_p.exists()} y={y_p.exists()}"); return

    X = pd.read_parquet(ds_p)
    Y = pd.read_parquet(y_p)

    # 型/欠損整備
    for df in (X, Y):
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    X = X.dropna(subset=["ticker","date"]).sort_values(["ticker","date"])
    Y = Y.dropna(subset=["ticker","date"]).sort_values(["ticker","date"])

    # 銘柄ごとにmerge_asof（右側=Yを必ず日付昇順に）
    outs = []
    for tkr, gX in X.groupby("ticker", sort=True):
        gY = Y[Y["ticker"]==tkr].sort_values("date")
        if gY.empty: continue
        mg = pd.merge_asof(
            gX.sort_values("date"),
            gY[["date"]+LABEL_COLS].sort_values("date"),
            on="date",
            direction="forward",
            tolerance=pd.Timedelta(days=10)
        )
        outs.append(mg)
    if not outs:
        print("no merged rows"); return
    df = pd.concat(outs, ignore_index=True)
    before = len(df)
    df = df.dropna(subset=LABEL_COLS)
    after = len(df)

    df.to_parquet(out, index=False)
    feat_cols = [c for c in df.columns if c not in (["ticker","date"]+LABEL_COLS)]
    print(f"final rows {after} / {before}, features {len(feat_cols)}, labels {len(LABEL_COLS)} -> {out}")
if __name__ == "__main__":
    main()
