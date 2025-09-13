# -*- coding: utf-8 -*-
import io, requests as rq, pandas as pd
from pathlib import Path

IN = Path("data/tmp/tickers_20141114.csv")
tick=[l.strip() for l in IN.read_text(encoding="utf-8").splitlines() if l.strip()]

ok, fail, samples_ok, samples_fail = [], [], [], []
for t in tick:
    code=t.split(".")[0].lower()
    url=f"https://stooq.com/q/d/l/?s={code}.jp&i=d"
    try:
        r=rq.get(url,timeout=10)
        df=pd.read_csv(io.StringIO(r.text))
        has= (df.shape[0]>=2) and ("Date" in df) and ("Close" in df)
        (ok if has else fail).append(t)
        if has and len(samples_ok)<5: samples_ok.append({"t":t,"rows":len(df)})
        if (not has) and len(samples_fail)<5: samples_fail.append({"t":t,"status":r.status_code,"len":len(r.text)})
    except Exception as e:
        fail.append(t)
        if len(samples_fail)<5: samples_fail.append({"t":t,"err":str(e)[:120]})
print({"ok_n":len(ok),"fail_n":len(fail),"ok_samples":samples_ok,"fail_samples":samples_fail})
# 成功ティッカーを書き出し
OUT=Path("data/tmp/tickers_20141114_stooq_ok.csv"); 
(pd.Series(ok)).to_csv(OUT,index=False,header=False)
print({"ok_list":str(OUT)})
