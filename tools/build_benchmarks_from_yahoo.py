import pandas as pd, pathlib, sys
from math import sqrt
ROOT=pathlib.Path("C:/AI/AlphaUltra")
BRONZE=ROOT/"data/bronze/yahoo_default/ohlcv.parquet"
GOLD=ROOT/"data/gold/yahoo_default/features.parquet"
AUX=ROOT/"data/aux"
AUX.mkdir(parents=True, exist_ok=True)

def load_yahoo():
    if BRONZE.exists():
        df=pd.read_parquet(BRONZE)
        # ensure columns
        need={"date","ticker","close"}
        if not need.issubset(set(df.columns)): raise SystemExit("bronze missing columns")
        return df[["date","ticker","close"]].copy()
    elif GOLD.exists():
        df=pd.read_parquet(GOLD)
        need={"date","ticker","close"}
        if not need.issubset(set(df.columns)): raise SystemExit("gold missing columns")
        return df[["date","ticker","close"]].copy()
    else:
        raise SystemExit("no yahoo dataset found")
def pick_symbol(df, candidates):
    tickers=set(df["ticker"].unique())
    for c in candidates:
        if c in tickers: return c
    return None

df=load_yahoo()
CAND={
 "NIKKEI225":["^N225","NIKKEI225","^NI225"],
 "TOPIX":["^TOPX","^TPX"],
 "SP500":["^GSPC"],
 "NASDAQ":["^IXIC"],
 "USDJPY":["JPY=X","USDJPY=X","USDJPY"],
 "GOLD":["GC=F","XAUUSD=X","XAUUSD"]
}

bench=None
used={}
for name, cands in CAND.items():
    t=pick_symbol(df,cands)
    if t is None: continue
    used[name]=t
    s=df[df["ticker"]==t][["date","close"]].rename(columns={"close":name})
    bench = s if bench is None else pd.merge(bench,s,how="outer",on="date")

if bench is None: raise SystemExit("no benchmark symbols found")
bench=bench.sort_values("date").reset_index(drop=True)
bench.to_csv(AUX/"benchmarks.csv", index=False)

# index_timeseries.csv（regime用）：優先 NIKKEI→SP500→NASDAQ の順でclose列に採用
idx=None
for k in ["NIKKEI225","SP500","NASDAQ"]:
    if k in bench.columns:
        idx=bench[["date",k]].rename(columns={k:"close"}).dropna()
        break
if idx is None:
    # どれも無い場合は先頭数列の1つをclose扱い
    cols=[c for c in bench.columns if c!="date"]
    idx=bench[["date",cols[0]]].rename(columns={cols[0]:"close"}).dropna()

idx.to_csv(AUX/"index_timeseries.csv", index=False)

# 参考: ベンチSharpeを吐く（quick）
ret = idx["close"].pct_change()
bench_sharpe = (ret.mean()/ret.std())*sqrt(252) if ret.std() and ret.notna().sum()>10 else 0.0
(pd.DataFrame([{"symbol_map":used, "bench_sharpe":bench_sharpe}])
 ).to_json(AUX/"bench_meta.json", orient="records", force_ascii=False)

print(f"[benchmarks] wrote {str(AUX/'benchmarks.csv')} cols={list(bench.columns)}")
print(f"[index_ts]   wrote {str(AUX/'index_timeseries.csv')} rows={len(idx)}")
