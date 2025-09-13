import argparse, pathlib, os, time, json, re
import pandas as pd
from bs4 import BeautifulSoup
try:
    import requests
except Exception:
    requests=None

def sget(sess, url):
    r=sess.get(url, timeout=15, headers={"User-Agent":"Mozilla/5.0"}); r.raise_for_status(); return r

def extract(html:str):
    soup=BeautifulSoup(html, "html.parser")
    ttl = soup.find(["h1","h2"])
    ttl = ttl.get_text(" ", strip=True) if ttl else ""
    cand = soup.find("div", attrs={"class": re.compile("(article|text|body)", re.I)}) or soup.find("section")
    txt  = cand.get_text(" ", strip=True) if cand else ""
    return ttl[:512], txt[:2000]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--in-parquet", required=True)
    ap.add_argument("--out-parquet", required=True)
    args=ap.parse_args()

    import pathlib, os; import pandas as pd; import sys
p=pathlib.Path(args.in_parquet)
if not p.exists(): print(f"[tdnet-html] missing {p}"); sys.exit(0)
df=pd.read_parquet(args.in_parquet)
    if df.empty: 
        print("[tdnet-html] empty input"); 
        pathlib.Path(args.out_parquet).parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(args.out_parquet, index=False); 
        return

    sess = requests.Session() if requests else None
    ck=os.getenv("KABUTAN_COOKIE","")
    if sess and ck: sess.headers.update({"Cookie": ck})

    titles=[]; snippets=[]
    for u in df["url"].fillna(""):
        if not (sess and u): titles.append(""); snippets.append(""); continue
        try:
            r=sget(sess, u); t,s = extract(r.text)
        except Exception:
            t,s="",""
        titles.append(t); snippets.append(s); time.sleep(0.2)
    df["title_html"]=titles; df["text_snippet"]=snippets
    pathlib.Path(args.out_parquet).parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(args.out_parquet, index=False)
    print("[tdnet-html] ->", args.out_parquet, "rows=", len(df))
if __name__=="__main__": main()

