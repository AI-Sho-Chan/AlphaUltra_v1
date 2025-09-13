import re, json, hashlib, unicodedata as U, pandas as pd
from pathlib import Path

def N(x):
    if x is None or (isinstance(x,float) and pd.isna(x)):
        return ""
    return U.normalize("NFKC", str(x)).strip()

def folder_ymd(p: Path):
    s = str(p)
    m = re.search(r"(20\d{2})[-_/](\d{2})[-_/](\d{2})", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    parts = p.parts
    for i in range(len(parts)-2):
        if re.fullmatch(r"20\d{2}", parts[i]) and re.fullmatch(r"\d{2}", parts[i+1]) and re.fullmatch(r"\d{2}", parts[i+2]):
            return f"{parts[i]}-{parts[i+1]}-{parts[i+2]}"
    m = re.search(r"(20\d{2})(\d{2})(\d{2})", s)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None

def pick(cols, cand):
    nm = {U.normalize("NFKC", c).lower(): c for c in cols}
    for k in cand:
        kk = U.normalize("NFKC", k).lower()
        for low, orig in nm.items():
            if kk in low:
                return orig
    return None

SRC = Path(r"C:\AI\AlphaUltra_v1\data\raw\kabutan")
DST = Path(r"C:\AI\AlphaUltra_v1\data\raw\tdnet_new"); DST.mkdir(parents=True, exist_ok=True)
RMIN, RMAX = "2019-09-01", "2019-09-30"

CODE_COLS  = ["コード","銘柄コード","証券コード","code","sec_code"]
TITLE_COLS = ["タイトル","件名","見出し","表題","題名","headline","subject","title","title_html","text_snippet"]
DT_COLS    = ["掲載日時","発表日時","開示日時","公表日時","更新日時","日時","date","datetime","published","timestamp"]
DATE_COLS  = ["掲載日","発表日","開示日","公表日","日付","date"]
TIME_COLS  = ["掲載時刻","発表時刻","開示時刻","公表時刻","時刻","time"]

files = list(SRC.rglob("*.csv")) + list(SRC.rglob("*.CSV")) + list(SRC.rglob("*tdnet*.tsv"))
w = 0; uniq = set(); by_year = {}

for fp in files:
    ymd = folder_ymd(fp)
    if not ymd or not (RMIN <= ymd <= RMAX):
        continue
    try:
        if fp.suffix.lower() == ".tsv":
            df = pd.read_csv(fp, sep="\t", encoding="utf-8-sig")
        else:
            try:
                df = pd.read_csv(fp, encoding="utf-8-sig")
            except UnicodeDecodeError:
                df = pd.read_csv(fp, encoding="cp932")
    except Exception:
        continue

    c_code  = pick(df.columns, CODE_COLS)
    if not c_code:
        continue
    c_title = pick(df.columns, TITLE_COLS)
    c_dt    = pick(df.columns, DT_COLS)
    c_d     = pick(df.columns, DATE_COLS)
    c_t     = pick(df.columns, TIME_COLS)

    for _, r in df.iterrows():
        m = re.search(r"(?<!\d)(\d{4})(?!\d)", N(r.get(c_code)))
        if not m:
            continue
        code4 = m.group(1)
        if not (1300 <= int(code4) <= 9999):
            continue
        ticker = f"{code4}.T"

        title = N(r.get(c_title)) if c_title else ""
        if len(title) < 2:
            continue

        dt = None
        if c_dt:
            dt = pd.to_datetime(N(r.get(c_dt)), errors="coerce")
        if (dt is None or pd.isna(dt)) and c_d:
            if c_t:
                dt = pd.to_datetime(N(r.get(c_d)) + " " + N(r.get(c_t)), errors="coerce")
            else:
                dt = pd.to_datetime(N(r.get(c_d)), errors="coerce")
        if dt is None or pd.isna(dt):
            dt = pd.to_datetime(ymd + " 15:00:00")

        d = str(pd.to_datetime(dt).normalize().date())
        y, m2, d2 = d.split("-")
        outdir = DST / y / m2 / d2; outdir.mkdir(parents=True, exist_ok=True)

        sid = hashlib.sha1(f"{ticker}|{dt.strftime('%Y-%m-%d %H:%M:%S')}|{title}".encode("utf-8")).hexdigest()[:16]
        out = outdir / f"{ticker}_{sid}.json"
        if out.exists():
            continue

        rec = {"ticker": ticker, "code4": code4, "title": title,
               "published_at_jst": dt.strftime("%Y-%m-%d %H:%M:%S"),
               "date": d, "event_type": "other", "source": "kabutan"}
        out.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
        w += 1; uniq.add(ticker); by_year[y] = by_year.get(y, 0) + 1

paths = list(DST.rglob("*.json"))
def ymd_of(p):
    m = re.search(r"(20\d{2})[\\/](\d{2})[\\/](\d{2})", str(p))
    return "-".join(m.groups()) if m else None

dates = sorted([ymd_of(p) for p in paths if ymd_of(p)])
print({"json_files": len(paths), "tickers": len(uniq),
       "date_min": dates[0] if dates else None, "date_max": dates[-1] if dates else None,
       "by_year": dict(sorted(by_year.items()))})
