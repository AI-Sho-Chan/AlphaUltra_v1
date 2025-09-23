import sys, traceback, importlib.util, pathlib, time
print("[probe] launcher start", flush=True)
root = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("t6", str(root/"scripts"/"model_lightgbm_v2.py"))
m = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(m)
    # 最低限のパッチ: adj_close → px_close フォールバックの関数を注入
    def ensure_liquidity_cols(df, px):
        import pandas as pd
        if px is None or getattr(px,"empty",True): return df
        px = px.copy()
        if "date" in px.columns:
            px["date"] = pd.to_datetime(px["date"], errors="coerce").dt.tz_localize(None)
        price_col = "adj_close" if "adj_close" in px.columns else ("px_close" if "px_close" in px.columns else None)
        if price_col is None: return df
        if "volume" not in px.columns: px["volume"] = 0.0
        if "addv_3m" not in px.columns:
            px = px.sort_values(["ticker","date"])
            turn = px[price_col].astype("float64") * px["volume"].astype("float64")
            px["addv_3m"] = (turn.groupby(px["ticker"]).rolling(63, min_periods=20).mean()
                             .reset_index(level=0, drop=True))
        px = px.rename(columns={price_col:"px_close"})
        keep = [c for c in ["ticker","date","px_close","addv_3m"] if c in px.columns]
        return df.merge(px[keep], on=["ticker","date"], how="left")
    m.ensure_liquidity_cols = ensure_liquidity_cols
    print("[probe] call main()", flush=True)
    sys.argv = ["model_lightgbm_v2.py"] + sys.argv[1:]
    m.main()
    print("[probe] main() returned", flush=True)
except SystemExit as e:
    print(f"[probe] SystemExit: code={e.code}", flush=True); raise
except Exception:
    print("[probe] EXCEPTION ↓↓↓", flush=True)
    traceback.print_exc()
    print("[probe] EXCEPTION ↑↑↑", flush=True)
    sys.exit(1)
finally:
    print("[probe] launcher end", flush=True)
