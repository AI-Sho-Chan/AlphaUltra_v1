import pandas as pd, json, re, hashlib, unicodedata as U
from pathlib import Path
def N(x): 
    if x is None or (isinstance(x,float) and pd.isna(x)): return ""
    return U.normalize("NFKC", str(x)).strip()

SRC = Path(r"C:\AI\AlphaUltra\data\bronze\tdnet\tdnet_day_with_html_20190910.parquet")
DST = Path(r"C:\AI\AlphaUltra_v1\data\raw\tdnet"); DST.mkdir(parents=True, exist_ok=True)

df = pd.read_parquet(SRC)
w = 0
for _, r in df.iterrows():
    # コード
    code_txt = N(r.get("コード")) + " " + N(r.get("URL")) + " " + N(r.get("detail_url")) + " " + N(r.get("添付URL"))
    m = re.search(r"(?<!\d)(\d{4})(?!\d)", code_txt)
    if not m: 
        continue
    code4 = m.group(1); ticker = f"{code4}.T"

    # 日時（「日付」「時刻」優先）
    dt = pd.to_datetime(N(r.get("日付")) + " " + N(r.get("時刻")), errors="coerce")
    if pd.isna(dt):
        for k in ["掲載日時","発表日時","開示日時","公表日時","更新日時","日時","date","datetime","published","timestamp"]:
            v = N(r.get(k))
            if v:
                cand = pd.to_datetime(v, errors="coerce")
                if pd.notna(cand): dt = cand; break
    if pd.isna(dt): 
        continue
    d = str(pd.to_datetime(dt).normalize().date())
    y,mn,dd = d.split("-")
    outdir = DST / y / mn / dd; outdir.mkdir(parents=True, exist_ok=True)

    # タイトル
    title = None
    for k in ["タイトル","title_html","text_snippet","件名","見出し","表題","題名","開示内容","headline","subject"]:
        t = N(r.get(k))
        if len(t) >= 2: title = t; break
    if not title: 
        continue

    sid = hashlib.sha1(f"{ticker}|{dt.strftime('%Y-%m-%d %H:%M:%S')}|{title}".encode("utf-8")).hexdigest()[:16]
    out = outdir / f"{ticker}_{sid}.json"
    if out.exists(): 
        continue
    rec = {
        "ticker": ticker, "code4": code4, "title": title,
        "published_at_jst": dt.strftime("%Y-%m-%d %H:%M:%S"),
        "date": d, "event_type": "other", "source": "kabutan",
    }
    url = N(r.get("URL")); pdf = N(r.get("添付URL")); det = N(r.get("detail_url"))
    if url: rec["url_detail"] = url
    if det and not rec.get("url_detail"): rec["url_detail"] = det
    if pdf: rec["url_pdf"] = pdf
    out.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
    w += 1

print({"written": w})
