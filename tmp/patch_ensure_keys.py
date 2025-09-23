from pathlib import Path
f = Path("scripts/model_lightgbm_v2.py")
src = f.read_text(encoding="utf-8")

marker = "    # === end harden ==="
add = """
    # === key normalization ===
    # normalize column names
    px.columns = [str(c) for c in px.columns]
    # drop duplicate-named columns keeping first
    import pandas as pd, numpy as np
    if hasattr(px.columns, "duplicated") and px.columns.duplicated(keep="first").any():
        px = px.loc[:, ~px.columns.duplicated(keep="first")].copy()
    # decide date-like column
    date_col = None
    for c in ("eff_date","date","Date","trade_date","dt"):
        if c in px.columns:
            date_col = c; break
    if date_col is None:
        dtc = [c for c in px.columns if np.issubdtype(px[c].dtype, np.datetime64)]
        if dtc: date_col = dtc[0]
    if date_col is None:
        raise KeyError("no date-like column in prices")
    # ensure datetime and eff_date
    px[date_col] = pd.to_datetime(px[date_col], errors="coerce")
    if "eff_date" not in px.columns:
        px["eff_date"] = px[date_col]
    # unique key on ticker, eff_date
    if "ticker" not in px.columns:
        raise KeyError("ticker missing in prices")
    px = px.dropna(subset=["ticker","eff_date"]).drop_duplicates(["ticker","eff_date"]).copy()
    # compute addv if needed
    if "volume" not in px.columns:
        for v in ("volume","vol","Volume","volume_adj"):
            if v in px.columns:
                if v != "volume": px["volume"] = px[v]
                break
    if "volume" not in px.columns: px["volume"] = 0
    if "addv_3m" not in px.columns and "adj_close" in px.columns:
        # simple proxy if rolling addv not present
        try:
            px = px.sort_values(["ticker","eff_date"])
            px["addv_3m"] = px.groupby("ticker")["adj_close"].transform(lambda s: s.rolling(63, min_periods=1).mean()) * \
                            px.groupby("ticker")["volume"].transform(lambda s: s.rolling(63, min_periods=1).mean())
        except Exception:
            px["addv_3m"] = pd.NA
    # === end key normalization ===
"""
if marker not in src:
    raise SystemExit({"error":"patch anchor not found"})
f.write_text(src.replace(marker, marker+add), encoding="utf-8")
print({"patched": True})
