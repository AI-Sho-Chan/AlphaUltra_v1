# -*- coding: utf-8 -*-
import re, pandas as pd
from pathlib import Path
FEAT=Path("data/proc/features_tdnet/tdnet_event_features.parquet")
OUT =Path("data/tmp/tickers_2014.csv"); OUT.parent.mkdir(parents=True, exist_ok=True)
d=pd.read_parquet(FEAT,columns=["ticker","date"])
d["date"]=pd.to_datetime(d["date"])
win=d[(d["date"]>="2014-01-01")&(d["date"]<="2014-12-31")]
tick=sorted(t for t in win["ticker"].astype(str).unique() if re.match(r"^\d{4}\.T$",t))
pd.Series(tick).to_csv(OUT,index=False,header=False)
print({"tickers_2014":len(tick),"out":str(OUT)})
