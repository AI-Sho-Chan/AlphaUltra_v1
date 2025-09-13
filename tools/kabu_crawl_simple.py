# -*- coding: utf-8 -*-
import os,re,csv,time,requests as rq
from pathlib import Path

BASE=Path(r"C:\AI\AlphaUltra_v1\data\raw\kabutan"); BASE.mkdir(parents=True,exist_ok=True)

def H():
    c=os.environ.get("KABUTAN_COOKIE","").strip()
    if not c: raise SystemExit("[crawl] KABUTAN_COOKIE not set")
    return {"Cookie":c,"User-Agent":"alphaai-kabutan-crawler","Accept-Language":"ja-JP"}

def fetch(d, page):
    url=f"https://kabutan.jp/disclosures/?date={d}&page={page}"
    r=rq.get(url,headers=H(),timeout=20); r.raise_for_status(); return r.text

def parse(html:str):
    rows=[]
    for m in re.finditer(r'data-code="(\d{4})".*?(?:datetime="([^"]*)")?.*?class="title">(.+?)</a>.*?href="([^"]+)"', html, re.S):
        code,dt,title,href=m.groups()
        title=re.sub(r"<.*?>","",title).strip()
        url=("https://kabutan.jp"+href) if href.startswith("/") else href
        rows.append((code,dt,title,url))
    if not rows:
        for m in re.finditer(r'href="(/disclosures/[^"]+)".*?>(.+?)</a>', html, re.S):
            href,title=m.groups(); title=re.sub(r"<.*?>","",title).strip()
            cc=re.search(r'code=(\d{4})',href) or re.search(r'/(\d{4})(?:[/?#]|$)',href)
            if cc: rows.append((cc.group(1),"",title,"https://kabutan.jp"+href))
    return rows

def crawl_day(d:str, sleep=0.3, max_pages=0):
    outdir=BASE/d; outdir.mkdir(parents=True,exist_ok=True)
    dst=outdir/"tdnet.csv"; fresh=not dst.exists()
    with dst.open("a",newline="",encoding="utf-8-sig") as f:
        w=csv.writer(f); 
        if fresh: w.writerow(["コード","掲載日時","タイトル","URL"])
        total=0; page=1; guard=None
        while True:
            html=fetch(d,page); rows=parse(html)
            if not rows: break
            sig=(rows[0][0], rows[0][1], rows[0][2])
            if sig==guard: break
            guard=sig
            w.writerows(rows); total+=len(rows); page+=1
            if max_pages and page>max_pages: break
            time.sleep(sleep)
    return total, page-1
