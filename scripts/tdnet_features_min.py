from pathlib import Path
import pandas as pd, sys

inp = Path(r"C:\AI\AlphaUltra_v1\data\proc\features_tdnet\tdnet_events_raw.parquet")
out = Path(r"C:\AI\AlphaUltra_v1\data\proc\features_tdnet\tdnet_event_features.parquet")
out.parent.mkdir(parents=True, exist_ok=True)

df = pd.read_parquet(inp) if inp.exists() else pd.DataFrame()
if df.empty:
    print({"rows": 0}); sys.exit(0)

df["date"] = pd.to_datetime(df["date"])
et = df["event_type"].fillna("other").astype(str)

ohe = pd.get_dummies(et, prefix="", prefix_sep="").astype("int8")
pos = et.isin({"guidance_up","div_up","buyback","order","product","earnings"}).astype("int8")
neg = et.isin({"guidance_down","div_down","offering","lawsuit"}).astype("int8")

df["tone_pos"] = pos
df["tone_neg"] = neg
df["event_strength"] = 1.0

outdf = pd.concat([df[["ticker","date","event_type","tone_pos","tone_neg","event_strength"]], ohe], axis=1) \
          .sort_values(["ticker","date"])

outdf.to_parquet(out, index=False)
print({"rows": int(len(outdf)), "cols": int(outdf.shape[1]),
       "min_date": str(outdf["date"].min().date()), "max_date": str(outdf["date"].max().date())})
