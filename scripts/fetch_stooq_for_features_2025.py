import io, json, time, pandas as pd, requests as rq
from pathlib import Path

FEAT=Path("data/proc/features_tdnet/tdnet_event_features.parquet")
RAW =Path("data/raw/prices"); RAW.mkdir(parents=True, exist_ok=True)

d=pd.read_parquet(FEAT, columns=["ticker","date"])
d["date"]=pd.to_datetime(d["date"])
d=d[(d["date"]>="2025-06-01")&(d["date"]<="2025-08-31")]
tks=sorted({t for t in d["ticker"].astype(str) if t.endswith(".T")})

ok=fail=0
for t in tks:
    code=t.split(".")[0].lower()
    url=f"https://stooq.com/q/d/l/?s={code}.jp&i=d"
    try:
        r=rq.get(url, timeout=20)
        if r.status_code!=200 or len(r.text.splitlines())<2: fail+=1; continue
        df=pd.read_csv(io.StringIO(r.text))
        if "Date" not in df or "Close" not in df: fail+=1; continue
        out=pd.DataFrame({
            "date":pd.to_datetime(df["Date"]).dt.normalize(),
            "ticker":t,
            "adj_close":pd.to_numeric(df["Close"], errors="coerce"),
            "volume":pd.to_numeric(df.get("Volume"), errors="coerce")
        }).dropna(subset=["date","adj_close"])
        if out.empty: fail+=1; continue
        out.to_parquet(RAW/f"stooq_{code}.parquet", index=False)
        ok+=1; time.sleep(0.3)
    except: fail+=1
print(json.dumps({"tried":len(tks),"ok":ok,"fail":fail}, ensure_ascii=False))
