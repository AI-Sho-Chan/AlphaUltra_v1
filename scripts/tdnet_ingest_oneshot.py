import os, re, json
from pathlib import Path
import pandas as pd

RAW = Path("data/raw/tdnet")
SRC = Path("tmp/kabutan_exports")
OUT = Path("data/proc/features_tdnet/tdnet_events_raw.parquet")
OUT.parent.mkdir(parents=True, exist_ok=True)

recs = []
print(f"[1/3] scan json under {RAW}...")
for fp in RAW.rglob("*.json") if RAW.exists() else []:
    try:
        recs.append(json.loads(fp.read_text(encoding="utf-8")))
    except Exception:
        pass
print(f"  json records: {len(recs)}")

print(f"[2/3] scan csv under {SRC}...")
files = list(SRC.rglob("*.csv")) + list(SRC.rglob("*.CSV"))
for fp in files:
    try:
        df = pd.read_csv(fp, encoding="utf-8-sig")
    except UnicodeDecodeError:
        df = pd.read_csv(fp, encoding="cp932")
    cols = {c.lower().strip(): c for c in df.columns}
    def pick(*ks):
        for k in ks:
            if k in cols: return cols[k]
        return None
    c_code=pick("コード","code","銘柄コード")
    c_dt  =pick("掲載日時","published_at","日時","date","time")
    c_tit =pick("タイトル","title")
    c_body=pick("本文","body","内容","テキスト")
    if not (c_code and c_dt and c_tit): 
        continue
    tmp = df[[c_code,c_dt,c_tit]+([c_body] if c_body else [])].copy()
    tmp = tmp.rename(columns={c_code:"code", c_dt:"published_at_jst", c_tit:"title", (c_body or "body"):"body"})
    tmp["code4"] = tmp["code"].astype(str).str.extract(r"(\d{4})", expand=False)
    tmp = tmp[tmp["code4"].notna()]
    tmp["ticker"] = tmp["code4"] + ".T"
    recs += tmp.to_dict("records")
print(f"  csv files: {len(files)}")

def guess_event(title, body=None):
    t = (str(title or '') + ' ' + str(body or '')).lower()
    pats = {
      "buyback": r"自社株買|自己株式取得|share repurchase",
      "offering": r"公募|増資|第三者割当|cb|convertible|新株予約|希薄",
      "guidance_up": r"上方修正|上方見通し|raise|increase guidance",
      "guidance_down": r"下方修正|下方見通し|lower guidance",
      "div_up": r"増配", "div_down": r"減配",
      "ma": r"m&a|買収|売却|子会社|吸収合併|会社分割|スピンオフ",
      "product": r"承認|許可|販売開始|発売|臨床|clinical|approval|薬事",
      "personnel": r"社長|ceo|cfo|役員人事|取締役|resign",
      "lawsuit": r"訴訟|係争|調査|investigation",
      "capex": r"設備投資|建設計画|増設",
      "order": r"大型受注|受注|契約|award",
      "earnings": r"決算短信|決算|earnings|results"
    }
    for k,pat in pats.items():
        if re.search(pat, t): return k
    return "other"

rows = []
for r in recs:
    code4 = str(r.get("code4") or r.get("code") or "")
    if not code4 and r.get("ticker"):
        m = re.match(r"(\d{4})", str(r["ticker"])); code4 = m.group(1) if m else ""
    ticker = r.get("ticker") or (code4.zfill(4)+".T" if code4 else None)
    if not ticker: 
        continue
    padt = r.get("published_at_jst") or r.get("announce_dt_jst") or r.get("published_at") or r.get("datetime")
    dt = pd.to_datetime(padt, errors="coerce")
    if pd.isna(dt): 
        continue
    date = pd.to_datetime(dt).normalize()
    title = r.get("title"); body = r.get("body")
    et = r.get("event_type") or guess_event(title, body)
    rows.append({
        "ticker": ticker, "code4": code4 if code4 else None,
        "title": None if title is None else str(title),
        "body": None if body is None else str(body),
        "published_at_jst": str(pd.to_datetime(dt)),
        "date": date, "event_type": et,
        "source": r.get("source") or "kabutan/json"
    })

df = pd.DataFrame(rows).drop_duplicates(subset=["ticker","title","published_at_jst"])
df.to_parquet(OUT, index=False)
print({"rows": int(len(df)),
       "min_date": None if df.empty else str(df["date"].min().date()),
       "max_date": None if df.empty else str(df["date"].max().date())})
