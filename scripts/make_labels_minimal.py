import pandas as pd, glob
from pathlib import Path

def pick_price(df: pd.DataFrame):
    for c in ["adj_close","Adj Close","Adj_Close","adjusted_close","close","Close","adj"]:
        if c in df.columns: return df[c].astype(float)
    num = df.select_dtypes(include=["float","int"])
    if not num.empty: return num.iloc[:,0]
    raise ValueError("price column not found")

def main():
    adj = Path("data/proc/adj_prices"); lab = Path("data/proc/labels"); lab.mkdir(parents=True, exist_ok=True)
    spy_p = adj/"SPY.parquet"
    if not spy_p.exists():
        print("SPY missing -> no labels"); (lab/"targets.parquet").touch(); return
    spy = pd.read_parquet(spy_p).copy()
    spy["date"] = pd.to_datetime(spy["date"], errors="coerce"); spy = spy.sort_values("date")
    p_spy = pick_price(spy); R_spy = {k: p_spy/p_spy.shift(k)-1 for k in (21,63,252)}
    labs=[]
    for p in adj.glob("*.parquet"):
        t = p.stem
        if t=="SPY": continue
        df = pd.read_parquet(p)
        if "date" not in df.columns: continue
        df["date"]=pd.to_datetime(df["date"], errors="coerce"); df=df.sort_values("date")
        px = pick_price(df)
        future_max = px.shift(-1).rolling(252, min_periods=1).max()
        y2x = (future_max/px >= 2.0).astype(int)
        rel = {k: (px/px.shift(k)-1) - R_spy[k].reindex(df["date"]).values for k in (21,63,252)}
        labs.append(pd.DataFrame({
            "ticker": t,
            "date": df["date"].dt.strftime("%Y-%m-%d"),
            "y_2x": y2x.values,
            "rel_1M": rel[21].values,
            "rel_3M": rel[63].values,
            "rel_12M": rel[252].values
        }))
    L = pd.concat(labs, ignore_index=True) if labs else pd.DataFrame(columns=["ticker","date","y_2x","rel_1M","rel_3M","rel_12M"])
    L.to_parquet(lab/"targets.parquet", index=False)
    print(f"labels {len(L)}")
if __name__ == "__main__": main()
