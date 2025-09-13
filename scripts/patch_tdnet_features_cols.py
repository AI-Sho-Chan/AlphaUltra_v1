import json
from pathlib import Path
import pandas as pd
from pandas.tseries.offsets import BDay

p=Path("data/proc/features_tdnet/tdnet_event_features.parquet")
df=pd.read_parquet(p)
need=["event_strength","novelty","tone_pos","tone_neg","tone_unc","event_cat","eff_date"]
added=[]
if "event_strength" not in df: df["event_strength"]=1.0; added.append("event_strength")
if "novelty" not in df: df["novelty"]=0.0; added.append("novelty")
if "tone_pos" not in df: df["tone_pos"]=0; added.append("tone_pos")
if "tone_neg" not in df: df["tone_neg"]=0; added.append("tone_neg")
if "tone_unc" not in df: df["tone_unc"]=0; added.append("tone_unc")
if "event_cat" not in df: 
    df["event_cat"]=df["event_type"] if "event_type" in df else "other"; added.append("event_cat")
df["date"]=pd.to_datetime(df["date"], errors="coerce")
if "eff_date" not in df:
    df["eff_date"]=(df["date"]+BDay(1)).dt.normalize(); added.append("eff_date")
df.to_parquet(p, index=False)
print(json.dumps({"rows":int(len(df)),"cols":int(df.shape[1]),"added":added}, ensure_ascii=False))
