import argparse, yaml
from pathlib import Path
import pandas as pd
import exchange_calendars as xc

def to_next_session(cal, d):
    ts = pd.Timestamp(d).tz_localize(None)
    try:
        return cal.date_to_session(ts, direction="next")
    except Exception:
        return cal.next_session(ts) if not cal.is_session(ts) else ts

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--config", default="configs/tdnet_model.yaml")
    args=ap.parse_args()
    cfg=yaml.safe_load(open(args.config,"r",encoding="utf-8"))
    tdnet_path = Path(cfg["paths"]["tdnet_features"])
    adj_root   = Path(cfg["paths"]["adj_root"])
    out_panel  = Path(cfg["paths"]["dataset_root"])/"tdnet_panel.parquet"
    out_panel.parent.mkdir(parents=True, exist_ok=True)

    td = pd.read_parquet(tdnet_path)
    td = td[td["ticker"].str.endswith(".T")].copy()
    cal = xc.get_calendar("XTKS")
    td["eff_date"] = td["date"].apply(lambda x: to_next_session(cal, x))

    # 価格が存在するティッカーのみ
    tickers = sorted(set(td["ticker"]))
    has_px = [t for t in tickers if (adj_root/f"{t}.parquet").exists()]
    td = td[td["ticker"].isin(has_px)]

    # 結合
    frames=[]
    for t in has_px:
        px = pd.read_parquet(adj_root/f"{t}.parquet")
        px["date"]=pd.to_datetime(px["date"]).dt.tz_localize(None)
        g = td[td["ticker"]==t][["ticker","eff_date","event_strength","novelty","tone_pos","tone_neg","tone_unc","event_cat"]].copy()
        g = g.rename(columns={"eff_date":"date"})
        m = g.merge(px, on="date", how="left")
        m["ticker"]=t
        frames.append(m)
    panel = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    panel.to_parquet(out_panel, index=False)
    print(f"[INFO] panel rows={len(panel)} -> {out_panel}")
if __name__=="__main__": main()
