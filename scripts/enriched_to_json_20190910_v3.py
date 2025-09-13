import pandas as pd, re, json, hashlib, unicodedata as U
from pathlib import Path
def N(x): 
    if x is None or (isinstance(x,float) and pd.isna(x)): return ""
    return U.normalize("NFKC", str(x)).strip()

def parse_dt(d,t):
    ds,ts=N(d),N(t)
    m=re.search(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})", ds) or re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", ds)
    if not m: return pd.NaT
    y,M,dy=int(m.group(1)),int(m.group(2)),int(m.group(3))
    hh,mm,ss=15,0,0
    mt=re.search(r"(\d{1,2}):(\d{2})(?::(\d{2}))?", ts) or re.search(r"(\d{1,2})時(\d{1,2})分(?:(\d{1,2})秒)?", ts)
    if mt:
        hh=int(mt.group(1)); mm=int(mt.group(2)); ss=int(mt.group(3) or 0)
    return pd.Timestamp(year=y, month=M, day=dy, hour=hh, minute=mm, second=ss)

SRC=Path(r"C:\AI\AlphaUltra\data\bronze\tdnet\tdnet_day_with_html_20190910.parquet")
DST=Path(r"C:\AI\AlphaUltra_v1\data\raw\tdnet"); DST.mkdir(parents=True, exist_ok=True)
df=pd.read_parquet(SRC)
w=0
for _,r in df.iterrows():
    code_txt=" ".join([N(r.get("コード")), N(r.get("URL")), N(r.get("detail_url")), N(r.get("添付URL"))])
    m=re.search(r"(?<!\d)(\d{4})(?!\d)", code_txt)
    if not m: 
        continue
    code4=m.group(1); ticker=f"{code4}.T"

    dt=parse_dt(r.get("日付"), r.get("時刻"))
    if pd.isna(dt):
        cand=pd.to_datetime(N(r.get("日付"))+" "+N(r.get("時刻")), errors="coerce")
        if pd.notna(cand): dt=cand
    if pd.isna(dt): 
        continue

    title=None
    for k in ["タイトル","title_html","text_snippet","件名","見出し","表題","題名","開示内容","headline","subject"]:
        v=N(r.get(k))
        if len(v)>=2:
            title=v; break
    if not title: 
        continue

    d=str(dt.normalize().date()); y,m,dd=d.split("-")
    outdir=DST/y/m/dd; outdir.mkdir(parents=True, exist_ok=True)
    sid=hashlib.sha1(f"{ticker}|{dt.strftime('%Y-%m-%d %H:%M:%S')}|{title}".encode("utf-8")).hexdigest()[:16]
    out=outdir/f"{ticker}_{sid}.json"
    if out.exists(): 
        continue

    rec={"ticker":ticker,"code4":code4,"title":title,
         "published_at_jst":dt.strftime("%Y-%m-%d %H:%M:%S"),
         "date":d,"event_type":"other","source":"kabutan"}
    url=N(r.get("URL")); pdf=N(r.get("添付URL")); det=N(r.get("detail_url"))
    if url: rec["url_detail"]=url
    elif det: rec["url_detail"]=det
    if pdf: rec["url_pdf"]=pdf

    out.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
    w+=1

print({"written": w})
