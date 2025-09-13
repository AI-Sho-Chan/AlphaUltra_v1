import json
from pathlib import Path
import pandas as pd
from pandas.tseries.offsets import BDay

p = Path("data/proc/features_tdnet/tdnet_event_features.parquet")
df = pd.read_parquet(p)
added = []

if "novelty" not in df.columns:
    df["novelty"] = 0.0; added.append("novelty")
if "tone_unc" not in df.columns:
    df["tone_unc"] = 0; added.append("tone_unc")
if "event_cat" not in df.columns:
    df["event_cat"] = df["event_type"] if "event_type" in df.columns else "other"
    added.append("event_cat")
if "eff_date" not in df.columns:
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["eff_date"] = (df["date"] + BDay(1)).dt.normalize()
    added.append("eff_date")

out = {"rows": int(len(df)), "cols": int(df.shape[1]), "added": added}
df.to_parquet(p, index=False)
print(json.dumps(out, ensure_ascii=False))
