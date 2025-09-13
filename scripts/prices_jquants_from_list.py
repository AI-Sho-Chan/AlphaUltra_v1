# -*- coding: utf-8 -*-
# scripts/prices_jquants_from_list.py
import os, sys, time, json, io, re
from pathlib import Path
import requests as rq
import pandas as pd

LIST = Path(sys.argv[1]) if len(sys.argv)>1 else Path("data/tmp/tickers_20141114.csv")
RAW  = Path("data/raw/prices"); RAW.mkdir(parents=True, exist_ok=True)
TOK  = Path(".secrets/jq_tokens.json"); TOK.parent.mkdir(parents=True, exist_ok=True)

EMAIL = os.environ.get("JQ_EMAIL"); PASS = os.environ.get("JQ_PASSWORD")
assert EMAIL and PASS, "Set JQ_EMAIL / JQ_PASSWORD first."

AUTH_USER   = "https://api.jquants.com/v1/token/auth_user"
AUTH_REFRESH= "https://api.jquants.com/v1/token/auth_refresh"
DAILY_QUOTES= "https://api.jquants.com/v1/prices/daily_quotes"

def _save_tokens(d): TOK.write_text(json.dumps(d), encoding="utf-8")
def _load_tokens():
    if TOK.exists():
        try: return json.loads(TOK.read_text(encoding="utf-8"))
        except: return {}
    return {}

def _get_idtoken():
    t=_load_tokens()
    # refreshTokenがあれば更新
    if t.get("refreshToken"):
        r=rq.post(AUTH_REFRESH, params={"refreshtoken": t["refreshToken"]}, timeout=15)
        if r.ok and r.json().get("idToken"):
            t["idToken"]=r.json()["idToken"]; _save_tokens(t); return t["idToken"]
    # なければauth_user
    r=rq.post(AUTH_USER, json={"mailaddress": EMAIL, "password": PASS}, timeout=15)
    r.raise_for_status()
    rt=r.json().get("refreshToken"); assert rt, "No refreshToken"
    t={"refreshToken": rt}
    r2=rq.post(AUTH_REFRESH, params={"refreshtoken": rt}, timeout=15)
    r2.raise_for_status()
    it=r2.json().get("idToken"); assert it, "No idToken"
    t["idToken"]=it; _save_tokens(t); return it

def jq_fetch_day(code4, start="2013-01-01", end="2015-12-31", tries=3):
    it=_get_idtoken()
    for k in range(tries):
        h={"Authorization": f"Bearer {it}"}
        r=rq.get(DAILY_QUOTES, params={"code": code4, "from": start, "to": end}, headers=h, timeout=30)
        if r.status_code==401:  # トークン失効
            it=_get_idtoken(); continue
        if not r.ok: time.sleep(1.0*(k+1)); continue
        j=r.json() or {}
        rows=j.get("daily_quotes") or j.get("data") or []
        if not rows: return None
        df=pd.DataFrame(rows)
        if not {"Date","Close"}.issubset(df.columns): return None
        out=pd.DataFrame({
            "ticker": f"{code4}.T",
            "date":   pd.to_datetime(df["Date"]).dt.normalize(),
            "adj_close": pd.to_numeric(df["Close"], errors="coerce"),
            "volume":    pd.to_numeric(df.get("Volume"), errors="coerce")
        }).dropna(subset=["date","adj_close"])
        return out if not out.empty else None
    return None

def main():
    tick=[l.strip() for l in LIST.read_text(encoding="utf-8").splitlines() if l.strip()]
    # 4桁.T かつ 1300–9999 に限定
    valid=[]
    for t in tick:
        m=re.fullmatch(r"(\d{4})\.T", t)
        if not m: continue
        n=int(m.group(1))
        if 1300<=n<=9999: valid.append(m.group(1))
    ok=fail=0; samples=[]
    for i,code4 in enumerate(valid,1):
        # 既存キャッシュがあればskip（jquants_####.parquet）
        outp=RAW/f"jquants_{code4.lower()}.parquet"
        if outp.exists(): ok+=1; continue
        df=jq_fetch_day(code4)
        if df is not None:
            df.to_parquet(outp, index=False); ok+=1
            if len(samples)<5: samples.append({"code":code4, "rows": int(len(df))})
        else:
            fail+=1
        if i%50==0: time.sleep(0.5)
    print({"list": str(LIST), "todo": len(valid), "ok": ok, "fail": fail, "samples": samples})
if __name__=="__main__":
    main()
