# -*- coding: utf-8 -*-
import re, pandas as pd
from pathlib import Path
P=Path("data/proc/dataset/tdnet_panel.parquet")
OUT=Path("data/tmp/tickers_2014.csv"); OUT.parent.mkdir(parents=True,exist_ok=True)
df=pd.read_parquet(P,columns=["ticker","date"]); df["date"]=pd.to_datetime(df["date"])
win=df[(df["date"]>="2014-01-01")&(df["date"]<="2014-12-31")]
tick=sorted(t for t in win["ticker"].astype(str).unique() if re.match(r"^\d{4}\.T$",t))
pd.Series(tick).to_csv(OUT,index=False,header=False)
print({"tickers_2014":len(tick),"out":str(OUT)})
