import argparse, pathlib, re
import pandas as pd
import numpy as np

ROOT = pathlib.Path(r"C:\AI\AlphaUltra")
BRZ  = ROOT / "data/bronze/tdnet"
EV   = ROOT / "data/gold/events"

def _col(df, *names, fill=""):
    for n in names:
        if n in df.columns:
            return df[n]
    return pd.Series([fill]*len(df))

def _parse_event_time(row):
    d = str(row.get("日付","")).strip()
    t = str(row.get("時刻","")).strip()
    for fmt in ("%y/%m/%d %H:%M", "%Y/%m/%d %H:%M"):
        try: return pd.to_datetime(t, format=fmt, errors="raise")
        except Exception: pass
    for fmt in ("%H:%M", "%H:%M:%S"):
        try: return pd.to_datetime(f"{d} {t}", format=f"%Y-%m-%d {fmt}", errors="raise")
        except Exception: pass
    return pd.to_datetime(f"{d} {t}", errors="coerce")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)  # YYYY-MM-DD
    args = ap.parse_args()
    ymd = args.date; ymdc = ymd.replace("-","")

    pq_in  = BRZ / f"tdnet_day_with_html_{ymdc}.parquet"
    if not pq_in.exists():
        print(f"[events] missing {pq_in}"); return
    df = pd.read_parquet(pq_in)
    if df.empty:
        print(f"[events] {ymd} empty"); return

    code     = _col(df, "コード", "code").astype(str)
    category = _col(df, "区分", "category").astype(str)
    title    = _col(df, "タイトル", "title").astype(str)
    url_used = _col(df, "url_used", "URL", "url", fill="").astype(str)
    t_html   = _col(df, "title_html", fill="")
    t_snip   = _col(df, "text_snippet", fill="")

    out = pd.DataFrame()
    out["ticker"]     = code
    out["event_time"] = df.apply(_parse_event_time, axis=1)
    out["source"]     = "TDNET"
    out["category"]   = category
    out["headline"]   = title
    out["url"]        = url_used

    # novelty: title_html -> text_snippet -> title （空白除去の長さベース）
    txt = t_html.fillna("").astype(str)
    m = (txt.str.len()==0)
    txt.loc[m] = t_snip.fillna("").astype(str).loc[m]
    m2 = (txt.str.len()==0)
    txt.loc[m2] = title.fillna("").astype(str).loc[m2]
    lens = txt.str.replace(r"\s+","",regex=True).str.len().to_numpy(float)
    out["novelty"] = np.tanh(lens/80.0).astype(float)

    # size_raw: 当面はASCII辞書のみ（NO-OCR）
    body = (title.astype(str) + " " + np.where(t_html.fillna("")=="", t_snip.fillna(""), t_html.fillna("")))
    score = np.zeros(len(body), dtype=float)
    for kw,w in [("TOB",0.8),("dividend",0.3),("share buyback",0.8),("public offering",-0.8)]:
        score += np.where(body.str.contains(re.escape(kw), case=False, na=False), w, 0.0)
    out["size_raw"] = score

    pq_out = EV / f"tdnet_events_{ymdc}.parquet"
    EV.mkdir(parents=True, exist_ok=True)
    out.to_parquet(pq_out, index=False)
    print(f"[events] -> {pq_out} rows={len(out)}")

if __name__ == "__main__":
    main()