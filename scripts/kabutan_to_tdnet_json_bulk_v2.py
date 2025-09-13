import re, json
from pathlib import Path
import pandas as pd

SRC = Path(r"C:\AI\AlphaUltra_v1\data\raw\kabutan")
DST = Path(r"C:\AI\AlphaUltra_v1\data\raw\tdnet"); DST.mkdir(parents=True, exist_ok=True)

def ymd_from_path(p: Path):
    m = re.search(r"(20\d{2})-(\d{2})-(\d{2})", str(p))
    return "-".join(m.groups()) if m else None

# 価格CSV誤読を除外するヘッダ集合
PRICE_KEYS = {"open","high","low","close","始値","高値","安値","終値"}

def pick_col(cols, keys):
    m = {c.lower().strip(): c for c in cols}
    for k in keys:
        for kc,orig in m.items():
            if k in kc: return orig
    return None

files = list(SRC.rglob("tdnet.csv"))
written = 0
for fp in files:
    try:
        try:
            df = pd.read_csv(fp, encoding="utf-8-sig")
        except UnicodeDecodeError:
            df = pd.read_csv(fp, encoding="cp932")
    except Exception:
        continue

    # 価格系CSVはスキップ
    low = {c.lower() for c in df.columns}
    if len(PRICE_KEYS & low) >= 3:
        continue

    # 列ゆらぎ対応
    c_code = pick_col(df.columns, ["コード","銘柄コード","code"])
    c_title= pick_col(df.columns, ["タイトル","件名","title","表題"])
    c_dt   = pick_col(df.columns, ["掲載日時","発表日時","公表日時","日時","date","datetime","published","time"])
    c_d    = pick_col(df.columns, ["掲載日","発表日","公表日","日付","date"])
    c_t    = pick_col(df.columns, ["掲載時刻","発表時刻","公表時刻","時刻","time"])
    c_body = pick_col(df.columns, ["本文","内容","テキスト","body"])
    c_url  = pick_col(df.columns, ["url","詳細","link"])
    c_pdf  = pick_col(df.columns, ["pdf"])

    # 必須：コードとタイトル。日時は列orフォルダ日付で補完。
    if not (c_code and c_title):
        continue

    use = pd.DataFrame({
        "code": df[c_code].astype(str) if c_code else "",
        "title": df[c_title].astype(str) if c_title else ""
    })
    # 日付時刻合成
    dt_series = None
    if c_dt:
        dt_series = pd.to_datetime(df[c_dt], errors="coerce")
    else:
        date_part = pd.to_datetime(df[c_d], errors="coerce") if c_d else None
        time_part = df[c_t].astype(str) if c_t else None
        if date_part is not None:
            if time_part is not None:
                dt_series = pd.to_datetime(date_part.astype(str)+" "+time_part, errors="coerce")
            else:
                dt_series = pd.to_datetime(date_part, errors="coerce")
    # フォルダ日付でフォールバック
    if dt_series is None or dt_series.isna().all():
        ddir = ymd_from_path(fp)
        if ddir:
            dt_series = pd.to_datetime(ddir+" 15:00:00")  # 保守的に15:00 JST
            dt_series = pd.Series([dt_series]*len(use))
        else:
            continue

    use["published_at_jst"] = dt_series
    use = use.dropna(subset=["published_at_jst"])
    if use.empty:
        continue

    # 4桁コード→JPティッカー
    use["code4"] = use["code"].str.extract(r"(\d{4})", expand=False)
    use = use.dropna(subset=["code4"])
    if use.empty:
        continue
    use["ticker"] = use["code4"].astype(str)+".T"
    use["date"] = pd.to_datetime(use["published_at_jst"]).dt.normalize()

    if c_body: use["body"] = df[c_body].astype(str)
    if c_url:  use["url_detail"] = df[c_url].astype(str)
    if c_pdf:  use["url_pdf"] = df[c_pdf].astype(str)

    # ざっくりイベント種別
    def evtype(t,b=""):
        s=(str(t)+" "+str(b)).lower()
        pats=[("buyback", r"自社株買|自己株式|share repurchase"),
              ("offering", r"公募|増資|第三者割当|cb|convertible|新株予約|希薄"),
              ("guidance_up", r"上方修正|上方見通し|raise|increase guidance"),
              ("guidance_down", r"下方修正|下方見通し|lower guidance"),
              ("div_up", r"増配"), ("div_down", r"減配"),
              ("earnings", r"決算短信|決算|earnings|results"),
              ("ma", r"m&a|買収|売却|子会社|吸収合併|会社分割|spin-?off|スピンオフ"),
              ("product", r"承認|許可|販売開始|発売|臨床|clinical|approval|薬事"),
              ("order", r"大型受注|受注|契約|award"),
              ("personnel", r"社長|ceo|cfo|役員人事|取締役|resign"),
              ("lawsuit", r"訴訟|係争|調査|investigation"),
              ("capex", r"設備投資|建設計画|増設")]
        for k,rgx in pats:
            if re.search(rgx, s): return k
        return "other"

    for _,r in use.iterrows():
        d = str(r["date"].date()); y,m,dd = d.split("-")
        outdir = DST / y / m / dd; outdir.mkdir(parents=True, exist_ok=True)
        rec = {
            "ticker": r["ticker"], "code4": r["code4"], "title": str(r["title"]),
            "published_at_jst": pd.to_datetime(r["published_at_jst"]).strftime("%Y-%m-%d %H:%M:%S"),
            "date": d, "event_type": evtype(r["title"], r.get("body","")), "source": "kabutan"
        }
        if "body" in use.columns: rec["body"] = None if pd.isna(r.get("body")) else str(r["body"])
        if "url_detail" in use.columns and not pd.isna(r.get("url_detail")): rec["url_detail"] = str(r["url_detail"])
        if "url_pdf" in use.columns and not pd.isna(r.get("url_pdf")): rec["url_pdf"] = str(r["url_pdf"])
        fname = f"{r['ticker']}_{pd.to_datetime(r['published_at_jst']).strftime('%H%M%S')}_{abs(hash(rec['title']))%1000000}.json"
        (outdir/fname).write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
        written += 1

# サマリ出力
paths = list(DST.rglob("*.json"))
def ymd(p): 
    m=re.search(r"(20\d{2})[\\/](\d{2})[\\/](\d{2})", str(p))
    return "-".join(m.groups()) if m else None
dates = sorted([ymd(p) for p in paths if ymd(p)])
print({"csv_files": len(files), "json_files": len(paths), "date_min": dates[0] if dates else None, "date_max": dates[-1] if dates else None})
