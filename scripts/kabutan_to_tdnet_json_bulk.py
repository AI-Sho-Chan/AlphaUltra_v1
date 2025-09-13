import re, json
from pathlib import Path
import pandas as pd

SRC = Path(r"C:\AI\AlphaUltra_v1\data\raw\kabutan")     # 旧リポからコピー済み 4378 CSV
DST = Path(r"C:\AI\AlphaUltra_v1\data\raw\tdnet")       # TDNET JSON 出力
DST.mkdir(parents=True, exist_ok=True)

def norm_cols(cols):
    m = {c.lower().strip(): c for c in cols}
    def pick(cands):
        for k in cands:
            for key in m.keys():
                if k in key:
                    return m[key]
        return None
    return {
        "code":  pick(["コード","銘柄コード","code"]),
        "dt":    pick(["掲載日時","発表日時","日時","date","time","published"]),
        "title": pick(["タイトル","件名","title"]),
        "body":  pick(["本文","内容","テキスト","body"]),
        "url":   pick(["url","詳細url","リンク"]),
        "pdf":   pick(["pdf"])
    }

def event_type_from(title, body=""):
    t=(str(title)+" "+str(body)).lower()
    pat = [
        ("buyback", r"自社株買|自己株式|share repurchase"),
        ("offering", r"公募|増資|第三者割当|cb|convertible|新株予約|希薄"),
        ("guidance_up", r"上方修正|上方見通し|raise|increase guidance"),
        ("guidance_down", r"下方修正|下方見通し|lower guidance"),
        ("div_up", r"増配"),
        ("div_down", r"減配"),
        ("ma", r"m&a|買収|売却|子会社|吸収合併|会社分割|spin\-?off|スピンオフ"),
        ("product", r"承認|許可|販売開始|発売|臨床|clinical|approval|薬事"),
        ("order", r"大型受注|受注|契約|award"),
        ("earnings", r"決算短信|決算|earnings|results"),
        ("personnel", r"社長|ceo|cfo|役員人事|取締役|resign"),
        ("lawsuit", r"訴訟|係争|調査|investigation"),
        ("capex", r"設備投資|建設計画|増設"),
    ]
    for name,rgx in pat:
        if re.search(rgx, t): return name
    return "other"

files = list(SRC.rglob("tdnet.csv"))
rows = 0
for fp in files:
    try:
        try:
            df = pd.read_csv(fp, encoding="utf-8-sig")
        except UnicodeDecodeError:
            df = pd.read_csv(fp, encoding="cp932")
    except Exception:
        continue
    cols = norm_cols(df.columns)
    req = [cols["code"], cols["dt"], cols["title"]]
    if any(c is None for c in req): 
        continue
    use = df[[cols["code"], cols["dt"], cols["title"]]].copy()
    if cols["body"]: use["body"] = df[cols["body"]]
    if cols["url"]:  use["url_detail"] = df[cols["url"]]
    if cols["pdf"]:  use["url_pdf"] = df[cols["pdf"]]
    use["code4"] = use[cols["code"]].astype(str).str.extract(r"(\d{4})", expand=False)
    use = use[use["code4"].notna()].copy()
    use["ticker"] = use["code4"] + ".T"
    use["published_at_jst"] = pd.to_datetime(use[cols["dt"]], errors="coerce")
    use = use[use["published_at_jst"].notna()].copy()
    use["date"] = use["published_at_jst"].dt.normalize()
    use["event_type"] = [event_type_from(t, b if "body" in use.columns else "") 
                         for t,b in zip(use[cols["title"]], use["body"] if "body" in use.columns else [""]*len(use))]
    for _,r in use.iterrows():
        d = str(r["date"].date())
        y,m,dd = d.split("-")
        outdir = DST / y / m / dd
        outdir.mkdir(parents=True, exist_ok=True)
        rec = {
            "ticker": r["ticker"],
            "code4": r["code4"],
            "title": str(r[cols["title"]]),
            "body": None if "body" not in use.columns or pd.isna(r.get("body")) else str(r["body"]),
            "published_at_jst": r["published_at_jst"].strftime("%Y-%m-%d %H:%M:%S"),
            "date": d,
            "event_type": r["event_type"],
            "source": "kabutan"
        }
        if "url_detail" in use.columns and not pd.isna(r.get("url_detail")):
            rec["url_detail"] = str(r["url_detail"])
        if "url_pdf" in use.columns and not pd.isna(r.get("url_pdf")):
            rec["url_pdf"] = str(r["url_pdf"])
        fname = f"{r['ticker']}_{r['published_at_jst'].strftime('%H%M%S')}_{abs(hash(rec['title']))%1000000}.json"
        (outdir / fname).write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
        rows += 1

# サマリ出力
import re as _re
paths = list(DST.rglob("*.json"))
def ymd(p): 
    m=_re.search(r"(20\d{2})[\\/](\d{2})[\\/](\d{2})", str(p))
    return "-".join(m.groups()) if m else None
dates = sorted([ymd(p) for p in paths if ymd(p)])
print({"csv_files": len(files), "json_files": len(paths), "date_min": dates[0] if dates else None, "date_max": dates[-1] if dates else None})
