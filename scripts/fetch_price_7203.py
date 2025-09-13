import io, pandas as pd, requests as rq, pathlib as P
P.Path("data/raw/prices").mkdir(parents=True, exist_ok=True)
url="https://stooq.com/q/d/l/?s=7203.jp&i=d"
df=pd.read_csv(io.StringIO(rq.get(url,timeout=20).text))
df=df.rename(columns={"Date":"date","Close":"adj_close","Volume":"volume"})
df["date"]=pd.to_datetime(df["date"]).dt.normalize()
df.insert(1,"ticker","7203.T")
df[["ticker","date","adj_close","volume"]].to_parquet("data/raw/prices/stooq_7203.parquet",index=False)
print(len(df))
