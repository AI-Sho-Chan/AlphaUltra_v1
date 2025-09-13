# -*- coding: utf-8 -*-
import pandas as pd, re, pathlib as P
csv=P.Path("data/tmp/tickers_20141114.csv")
t=[l.strip() for l in csv.read_text(encoding="utf-8").splitlines() if l.strip()]
print({"total":len(t),"head10":t[:10]})
