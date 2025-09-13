import json, re, unicodedata as U, pandas as pd
from pathlib import Path
from pandas.tseries.offsets import BDay

RAW=Path("data/raw/tdnet")
OUT=Path("data/proc/features_tdnet/tdnet_event_features.parquet"); OUT.parent.mkdir(parents=True, exist_ok=True)
RMIN=pd.Timestamp("2013-09-01"); RMAX=pd.Timestamp("2024-09-10")

def N(x): 
    if x is None: return ""
    if isinstance(x,float) and pd.isna(x): return ""
    return U.normalize("NFKC", str(x)).strip()

def get_date_from_path(p: Path):
    m=re.search(r"(20\d{2})[\\/](\d{2})[\\/](\d{2})", str(p))
    return pd.to_datetime("-".join(m.groups())) if m else pd.NaT

rows=[]
for fp in RAW.rglob("*.json"):
    try:
        j=json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        continue

    # 日付
    d = pd.to_datetime(j.get("date"), errors="coerce")
    if pd.isna(d):
        d = pd.to_datetime(j.get("published_at_jst"), errors="coerce")
    if pd.isna(d):
        d = get_date_from_path(fp)
    if pd.isna(d) or d<RMIN or d>RMAX:
        continue
    d=d.normalize()

    # コード推定
    code4 = j.get("code4")
    if code4 is None or not re.fullmatch(r"\d{4}", str(code4)):
        blob = " ".join([N(j.get(k)) for k in ["ticker","code4","title","body","url_detail","url_pdf"]])
        m=re.search(r"(?<!\d)(\d{4})(?!\d)", blob)
        code4 = m.group(1) if m else None
    if not code4:
        continue
    ticker = j.get("ticker")
    if not ticker or ".T" not in str(ticker):
        ticker = f"{code4}.T"

    et = N(j.get("event_type")) or "other"
    pos={"guidance_up","div_up","buyback","order","product","earnings"}
    neg={"guidance_down","div_down","offering","lawsuit"}
    rows.append({
        "ticker": ticker,
        "date": d,
        "eff_date": (d+BDay(1)).normalize(),
        "event_type": et,
        "event_cat": et,
        "event_strength": 1.0,
        "novelty": 0.0,
        "tone_pos": int(et in pos),
        "tone_neg": int(et in neg),
        "tone_unc": 0,
    })

df=pd.DataFrame(rows)
if df.empty:
    print({"rows":0}); exit()

df=df.drop_duplicates(subset=["ticker","date","event_type"])
df.to_parquet(OUT, index=False)
print({"rows":int(len(df)), "tickers":int(df["ticker"].nunique()),
       "date_min":str(df["date"].min().date()), "date_max":str(df["date"].max().date())})
