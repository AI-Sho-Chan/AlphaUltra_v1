import argparse, pathlib, json, pandas as pd, numpy as np, re

ROOT=pathlib.Path(r"C:\AI\AlphaUltra")
EV_DIR = ROOT/"data/gold/events"
PX_FEAT = ROOT/"data/gold/yahoo_default/features.parquet"
PX_LABEL= ROOT/"data/gold/yahoo_default/labels.parquet"
CAL    = EV_DIR/"calibration.json"
REP    = ROOT/"reports/event_study"

def load_events():
    files = sorted(EV_DIR.glob("tdnet_events_*.parquet"))
    if not files: return None
    dfs = [pd.read_parquet(p) for p in files]
    ev  = pd.concat(dfs, ignore_index=True)
    return ev

def load_prices():
    if pathlib.Path(PX_FEAT).exists():
        px = pd.read_parquet(PX_FEAT)
    else:
        return None
    px["date"]=pd.to_datetime(px["date"])
    # ret5 が無ければ close から作る
    if "ret5" not in px.columns:
        px = px.sort_values(["ticker","date"]).copy()
        if "close" in px.columns:
            px["ret5"] = px.groupby("ticker")["close"].pct_change(5)
        else:
            # ラベル側に fret5 があれば拾う
            if pathlib.Path(PX_LABEL).exists():
                lb=pd.read_parquet(PX_LABEL)
                if "fret5" in lb.columns:
                    lb["date"]=pd.to_datetime(lb["date"])
                    px = px.merge(lb[["date","ticker","fret5"]], on=["date","ticker"], how="left")
                    px = px.rename(columns={"fret5":"ret5"})
    return px

def normalize_ticker(s: pd.Series)->pd.Series:
    s = s.astype(str).str.strip()
    s = s.str.replace(r"[^0-9A-Za-z\.\-]", "", regex=True)
    # 4桁数字は .T を付ける
    s.loc[s.str.fullmatch(r"\d{4}")] = s.loc[s.str.fullmatch(r"\d{4}")] + ".T"
    return s

def main():
    ev = load_events()
    px = load_prices()
    if ev is None or ev.empty or px is None or px.empty:
        print("[evtstudy] missing events or prices"); return

    # 正規化
    ev = ev.dropna(subset=["ticker","event_time"]).copy()
    ev["date"]   = pd.to_datetime(ev["event_time"]).dt.normalize()
    ev["ticker"] = normalize_ticker(ev["ticker"])
    px_max = px["date"].max()

    # 価格がある範囲に切る（+5d計算のため、厳密には px_max まででOK）
    ev = ev[ev["date"] <= px_max]
    if ev.empty:
        print("[evtstudy] not enough events after date filter:", 0); return

    # JOIN
    merged = ev.merge(px[["date","ticker","ret5"]], on=["date","ticker"], how="left")
    merged = merged.dropna(subset=["ret5"])
    if len(merged) < 200:
        print("[evtstudy] not enough events:", len(merged)); return

    # 特徴（標準化）→ OLS
    X = merged[["novelty","size_raw"]].fillna(0.0).to_numpy()
    X = (X - X.mean(0))/(X.std(0)+1e-9)
    y = merged["ret5"].astype(float).to_numpy()
    w = np.linalg.lstsq(X, y, rcond=None)[0]
    cal={"w_novelty": float(w[0]), "w_size": float(w[1]), "bias": 0.0,
         "n": int(len(merged)), "px_max": str(px_max)}

    CAL.write_text(json.dumps(cal, ensure_ascii=False, indent=2), encoding="utf-8")
    REP.mkdir(parents=True, exist_ok=True)
    (REP/"summary.md").write_text(f"# Event Study\nn={len(merged)}\npx_max={px_max}\nw={cal}\n", encoding="utf-8")
    print("[evtstudy] wrote", CAL, "| n=", len(merged), "| px_max=", px_max)

if __name__=="__main__":
    main()