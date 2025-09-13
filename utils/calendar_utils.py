import pandas as pd
import exchange_calendars as xcals

def get_sessions(cal: str, start: str, end: str) -> pd.DatetimeIndex:
    c = xcals.get_calendar(cal)
    return c.sessions_in_range(pd.Timestamp(start), pd.Timestamp(end))

def align_to_anchor_calendar(df_px: pd.DataFrame, anchor_sessions: pd.DatetimeIndex) -> pd.DataFrame:
    out = df_px.reindex(anchor_sessions)
    price_cols = [c for c in out.columns if c in {"open","high","low","close","adj_close"}]
    if price_cols:
        out[price_cols] = out[price_cols].ffill()
    if "volume" in out.columns:
        out["volume"] = out["volume"].fillna(0)
    return out
