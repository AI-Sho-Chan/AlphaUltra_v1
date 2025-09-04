# -*- coding: utf-8 -*-
"""
TDNET features builder (safe date handling)
- 入力: data/raw/tdnet/YYYY/MM/DD/*.json
- 期間: configs YAML の params.start_date/end_date（YYYY-MM-DD）
- 出力: data/proc/features_tdnet/tdnet_event_features.parquet
  列: ticker,date,eff_date,event_type,event_cat,
      event_strength,novelty,tone_pos,tone_neg,tone_unc + one-hot (event_type_)
"""
import json, re, sys
from pathlib import Path
from datetime import date as _date
import pandas as pd
import numpy as np
import yaml
from pandas.tseries.offsets import BDay

def _to_date(x):
    if x is None: return None
    if isinstance(x, _date): return x
    if isinstance(x, str): return _date.fromisoformat(x.strip())
    return None

def load_cfg(p: Path):
    cfg = {"paths":{"tdnet_raw":"data/raw/tdnet",
                    "tdnet_features":"data/proc/features_tdnet/tdnet_event_features.parquet"},
           "params":{"start_date":None,"end_date":None}}
    if p.exists():
        with p.open("r", encoding="utf-8") as f:
            u = yaml.safe_load(f) or {}
        for k in ("paths","params"):
            if k in u: cfg[k].update(u[k] or {})
    return cfg

def iter_json_files(root: Path):
    for fp in root.rglob("*.json"):
        yield fp

def feature_rows_from_json(fp: Path):
    try:
        j = json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        return None
    t = j.get("ticker")
    d = j.get("date")
    et = (j.get("event_type") or "other")
    if not t or not d:
        # フォルダ名日付を使う
        m = re.search(r"(20\d{2})[\\/](\d{2})[\\/](\d{2})", str(fp))
        if m: d = "-".join(m.groups())
    if not t or not d:
        return None
    try:
        dt = pd.to_datetime(d, errors="coerce").normalize()
    except Exception:
        return None
    if pd.isna(dt): return None
    return {
        "ticker": str(t),
        "date": dt,
        "event_type": str(et),
        "event_cat": str(et),
        "event_strength": 1.0,
        "novelty": 0.0,
        "tone_pos": int(et in {"guidance_up","div_up","buyback","order","product","earnings"}),
        "tone_neg": int(et in {"guidance_down","div_down","offering","lawsuit"}),
        "tone_unc": 0
    }

def main():
    cfg = load_cfg(Path("configs/tdnet_A.yaml")) if "--config" not in sys.argv else load_cfg(Path(sys.argv[-1]))
    tdnet_root = Path(cfg["paths"]["tdnet_raw"])
    out_path   = Path(cfg["paths"]["tdnet_features"])
    start = _to_date(cfg["params"].get("start_date"))
    end   = _to_date(cfg["params"].get("end_date"))

    rows = []
    for fp in iter_json_files(tdnet_root):
        m = re.search(r"(20\d{2})[\\/](\d{2})[\\/](\d{2})", str(fp))
        ymd_dt = _date.fromisoformat("-".join(m.groups())) if m else None
        if start and ymd_dt and ymd_dt < start:  continue
        if end   and ymd_dt and ymd_dt > end:   continue
        r = feature_rows_from_json(fp)
        if r: rows.append(r)

    if not rows:
        print("[features] no rows. check data/raw/tdnet and date range"); sys.exit(0)

    df = pd.DataFrame(rows).drop_duplicates(["ticker","date","event_type"])
    df["eff_date"] = (df["date"] + BDay(1)).dt.normalize()

    # one-hot（event_type_XXXX）
    ohe = pd.get_dummies(df["event_type"], prefix="event_type", dtype="int8")
    out = pd.concat([df[["ticker","date","eff_date","event_type","event_cat",
                         "event_strength","novelty","tone_pos","tone_neg","tone_unc"]],
                     ohe], axis=1).sort_values(["ticker","date"]).reset_index(drop=True)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(out_path, index=False)
    print({"features_rows": int(len(out)),
           "tickers": int(out["ticker"].nunique()),
           "date_min": str(out["date"].min().date()),
           "date_max": str(out["date"].max().date()),
           "out": str(out_path)})
if __name__ == "__main__":
    main()
