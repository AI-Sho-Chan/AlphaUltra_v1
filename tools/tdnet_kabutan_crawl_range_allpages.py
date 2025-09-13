import os, re, csv, time, json, pathlib as P, requests as rq
from datetime import datetime
import argparse

def env_cookie():
    c = os.environ.get("KABUTAN_COOKIE","").strip()
    if not c: raise SystemExit("[crawl] KABUTAN_COOKIE not set")
    return {"Cookie": c, "User-Agent": "kabutan-crawler/alphaai"}

def fetch_page(d, page):
    # 例：?date=YYYY-MM-DD&page=2 のような一覧（実装済みのURL生成に置換）
    url = f"https://kabutan.jp/disclosures/?date={d}&page={page}"
    r = rq.get(url, headers=env_cookie(), timeout=20)
    r.raise_for_status()
    return r.text

def parse_to_rows(html):
    # 既存のHTML→行抽出ロジックを流用。最低でも code / datetime / title を返す
    rows=[]
    for m in re.finditer(r'data-code="(\d{4})".*?datetime="([^"]+)".*?class="title">(.+?)<', html, re.S):
        code, dt, title = m.group(1), m.group(2), re.sub(r"<.*?>","",m.group(3)).strip()
        rows.append((code, dt, title))
    return rows

def write_csv(dst_csv, rows, append=True):
    dst_csv.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append and dst_csv.exists() else "w"
    with dst_csv.open(mode, newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if mode=="w": w.writerow(["コード","掲載日時","タイトル"])
        for code,dt,title in rows:
            w.writerow([code,dt,title])

def crawl_day(d, out_dir, max_pages=0, sleep=0.3, resume=False):
    out_dir.mkdir(parents=True, exist_ok=True)
    dst = out_dir/"tdnet.csv"
    if resume and dst.exists():
        # 既存の最終行の件数で続行判定（簡易）
        pass
    page=1; total=0
    while True:
        html = fetch_page(d, page)
        rows = parse_to_rows(html)
        if not rows: break
        write_csv(dst, rows, append=True)
        total += len(rows)
        page += 1
        time.sleep(sleep)
        if max_pages>0 and page>max_pages: break
    return total, page-1

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True)
    ap.add_argument("--end",   required=True)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--sleep", type=float, default=0.3)
    ap.add_argument("--max-pages", type=int, default=0, help="0=all")
    args = ap.parse_args()

    d0 = datetime.fromisoformat(args.start).date()
    d1 = datetime.fromisoformat(args.end).date()
    cur = d0
    while cur <= d1:
        d = cur.isoformat()
        out = P.Path("data/raw/kabutan")/d
        try:
            rows, pages = crawl_day(d, out, max_pages=args["max_pages"] if isinstance(args, dict) and "max_pages" in args else args.max_pages, sleep=args.sleep, resume=args.resume)
            print(f"[crawl] {d} pages={pages} rows={rows} -> {out/'tdnet.csv'}")
        except Exception as e:
            print(f"[crawl][ERR] {d} {e}")
        cur = cur.fromordinal(cur.toordinal()+1)

if __name__ == "__main__":
    main()
