import argparse, pathlib, os, time, re, concurrent.futures as cf
import pandas as pd
from bs4 import BeautifulSoup
try:
    import requests
except Exception:
    requests=None

ROOT=pathlib.Path(r"C:\AI\AlphaUltra")
RAW = ROOT/"data/raw/kabutan"
BRZ = ROOT/"data/bronze/tdnet"

def pick_detail_url(row):
    # prefer non-PDF /disclosures detail url
    for k in ("url","url_en","URL","詳細URL"):
        u = str(row.get(k,"") or "").strip()
        if u and ("/disclosures" in u) and (not u.lower().endswith(".pdf")):
            return u
    return ""

def fetch_one(s, url):
    try:
        r=s.get(url, timeout=15, headers={"User-Agent":"Mozilla/5.0"}); r.raise_for_status()
        soup=BeautifulSoup(r.text,"html.parser")
        ttl=soup.find(["h1","h2"]); ttl=ttl.get_text(" ",strip=True) if ttl else ""
        div=soup.find("div", class_=re.compile("(article|text|body|detail)",re.I)) or soup.find("section")
        txt=div.get_text(" ",strip=True) if div else ""
        return ttl[:512], txt[:2000]
    except Exception:
        return "",""

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--date", required=True)     # YYYY-MM-DD
    ap.add_argument("--max-workers", type=int, default=6)
    ap.add_argument("--mode", choices=["important","all"], default="important")
    args=ap.parse_args()

    daydir = RAW/args.date
    csv = daydir/"tdnet.csv"
    if not csv.exists():
        print(f"[enrich] missing {csv}"); return

    df=pd.read_csv(csv)

    # 重要フィルタは日本語キーワードを使わず、当面は all と同等に扱う（文字化け回避）
    # 将来: カテゴリ正規化後に安全なフィルタを追加
    target = df.copy()

    # 決定された detail_url（非PDF）。PDFのみ行は空のまま
    target["detail_url"] = target.apply(pick_detail_url, axis=1)

    # 1) まず全行にフォールバック（タイトルを短文に、PDFがあればそれを url_used に）
    target["title_html"]   = ""
    target["text_snippet"] = target.get("タイトル","").astype(str)
    target["url_used"]     = target.get("添付URL","").astype(str)

    # 2) detail_url がある行だけ本文抽出で上書き
    has_detail = target["detail_url"]!=""
    if has_detail.any() and requests is not None:
        s=requests.Session()
        ck=os.getenv("KABUTAN_COOKIE","")
        if ck: s.headers.update({"Cookie": ck, "User-Agent":"Mozilla/5.0"})
        urls = target.loc[has_detail,"detail_url"].tolist()
        out=[]
        with cf.ThreadPoolExecutor(max_workers=args.max_workers) as ex:
            futs=[ex.submit(fetch_one, s, u) for u in urls]
            for f in cf.as_completed(futs):
                out.append(f.result())
        # 順序対応
        target.loc[has_detail,"title_html"]   = [x[0] for x in out]
        target.loc[has_detail,"text_snippet"] = [x[1] for x in out]
        target.loc[has_detail,"url_used"]     = target.loc[has_detail,"detail_url"]

    BRZ.mkdir(parents=True, exist_ok=True)
    pq = BRZ/f"tdnet_day_with_html_{args.date.replace('-','')}.parquet"
    target.to_parquet(pq, index=False)
    print(f"[enrich] -> {pq} rows={len(target)} (detail_used={int(has_detail.sum())})")

if __name__=="__main__": main()