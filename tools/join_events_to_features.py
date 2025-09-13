import argparse, pathlib, pandas as pd, numpy as np, re
ROOT=pathlib.Path(r"C:\AI\AlphaUltra")
feat=ROOT/"data/gold/yahoo_default/features.parquet"
evd =ROOT/"data/gold/events"
out=ROOT/"data/gold/yahoo_default/features_events.parquet"

def normalize_ticker(s: pd.Series)->pd.Series:
    s = s.astype(str).str.strip()
    s = s.str.replace(r"[^0-9A-Za-z\.\-]", "", regex=True)
    mask4 = s.str.fullmatch(r"\d{4}")
    s.loc[mask4] = s.loc[mask4] + ".T"
    return s

def next_date_map(dates):
    dates = np.array(sorted(pd.to_datetime(pd.unique(dates))))
    return {d: (dates[i+1] if i+1<len(dates) else d) for i,d in enumerate(dates)}

POS_KW = [r"自社株買", r"自己株式.*取得", r"上方修正", r"増配", r"配当.*引上げ", r"株主優待.*導入", r"TOB", r"買付"]
NEG_KW = [r"公募", r"新株発行", r"希薄", r"下方修正", r"減配|無配", r"第三者割当", r"希薄化", r"公募増資", r"PO"]

def polarity(cat,title):
    h = f"{cat or ''} {title or ''}"
    pos = sum(bool(re.search(p,h)) for p in POS_KW)
    neg = sum(bool(re.search(n,h)) for n in NEG_KW)
    if pos>neg: return 1.0
    if neg>pos: return -1.0
    return 0.0

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--date_min"); ap.add_argument("--date_max")
    args=ap.parse_args()

    df = pd.read_parquet(feat)
    df["date"]=pd.to_datetime(df["date"])
    df["ticker"]=normalize_ticker(df["ticker"])

    files=sorted(evd.glob("tdnet_events_*.parquet"))
    if files:
        ev = pd.concat([pd.read_parquet(p) for p in files], ignore_index=True)
        ev["date"]=pd.to_datetime(ev["event_time"]).dt.normalize()
        ev["ticker"]=normalize_ticker(ev["ticker"])
        # 極性
        cat = ev.get("category","").astype(str)
        ttl = ev.get("headline","").astype(str)
        ev["polarity"] = [polarity(c,t) for c,t in zip(cat,ttl)]
        # 場後→翌営業日へ
        hh = pd.to_datetime(ev["event_time"]).dt.hour
        d2n = next_date_map(df["date"])
        ev["target_date"] = ev["date"]
        ev.loc[hh>=16,"target_date"] = ev.loc[hh>=16,"date"].map(d2n)
        # 集約
        ev = ev.groupby(["target_date","ticker"])[["novelty","size_raw","polarity"]].max().reset_index()
        ev = ev.rename(columns={"target_date":"date"})
        df = df.merge(ev, on=["date","ticker"], how="left")
        for c in ("novelty","size_raw","polarity"):
            if c in df.columns: df[c]=df[c].fillna(0.0)
    else:
        for c in ("novelty","size_raw","polarity"): df[c]=0.0

    # 期間限定
    m = pd.Series(True, index=df.index)
    # （呼出し側で渡す）
    import pandas as _pd
    if args.date_min: m &= df["date"] >= _pd.to_datetime(args.date_min)
    if args.date_max: m &= df["date"] <= _pd.to_datetime(args.date_max)

    # 日次z
    for c in ("novelty","size_raw"):
        if c in df.columns:
            z = df.groupby("date")[c].transform(lambda s: (s - s.mean())/(s.std(ddof=0)+1e-9))
            df[f"{c}_z"] = z.fillna(0.0)

    # Top1%のみ（novelty_z基準）＋極性を符号として付与
    df["event_strength"]=0.0
    df["event_signal"] =0.0
    if "novelty_z" in df.columns:
        q = df.loc[m,"novelty_z"].quantile(0.99)
        sel = m & (df["novelty_z"]>=q)
        df.loc[sel,"event_strength"] = df.loc[sel,"novelty_z"]
        df.loc[sel,"event_signal"]  = df.loc[sel,"novelty_z"] * df.loc[sel,"polarity"]

    df.to_parquet(out, index=False)
    print("[JOIN] ->", out)

if __name__ == "__main__":
    main()