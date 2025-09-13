# -*- coding: utf-8 -*-
import pandas as pd
from pathlib import Path
paths=list(Path("data/raw/prices").glob("*.parquet"))
print({"files":len(paths)})
if paths:
    # 先頭最大20ファイルで概要
    import itertools as it
    sample=list(it.islice(paths,20))
    df=pd.concat([pd.read_parquet(p) for p in sample], ignore_index=True)
    cols=df.columns.tolist()
    print({"rows":len(df),
           "tickers":df["ticker"].nunique() if "ticker" in df else None,
           "date_min":str(df["date"].min().date()) if "date" in df else None,
           "date_max":str(df["date"].max().date()) if "date" in df else None,
           "cols":cols})
    print(df.head(5).to_string(index=False))
