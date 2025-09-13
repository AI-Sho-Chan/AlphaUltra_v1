# -*- coding: utf-8 -*-
import os, re, csv, asyncio, pathlib as P
from datetime import date, timedelta
from playwright.async_api import async_playwright

ROOT = P.Path("data/raw/kabutan"); ROOT.mkdir(parents=True, exist_ok=True)
COOKIE = os.environ.get("KABUTAN_COOKIE","").strip()
assert COOKIE, "KABUTAN_COOKIE not set"

HEADERS = {"Accept-Language":"ja-JP"}

def out_csv_path(d: str) -> P.Path:
    return ROOT / d / "tdnet.csv"

async def fetch_day(pw, d: str, sleep: float = 0.2, max_pages: int = 0):
    browser = await pw.chromium.launch(headless=True)
    ctx = await browser.new_context(extra_http_headers=HEADERS)
    # Cookie注入（name=value; の形式を分割）
    for kv in COOKIE.split(";"):
        if "=" in kv:
            name, value = kv.strip().split("=",1)
            await ctx.add_cookies([{"name":name.strip(),"value":value.strip(),"domain":"kabutan.jp","path":"/"}])

    page = await ctx.new_page()
    dst = out_csv_path(d)
    dst.parent.mkdir(parents=True, exist_ok=True)
    # CSVヘッダ（初回のみ）
    if not dst.exists():
        with dst.open("w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f).writerow(["コード","掲載日時","タイトル","URL"])

    total = 0
    pno = 1
    while True:
        url = f"https://kabutan.jp/disclosures/?date={d}&page={pno}"
        resp = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        if not resp or resp.status != 200:
            break

        # 各行抽出：記事カード or テーブル行に対応
        html = await page.content()
        rows = []

        # 1) data-code + datetime + タイトル（新UI想定）
        for m in re.finditer(r'data-code="(\d{4})".*?datetime="([^"]+)".*?class="title">(.+?)</a>.*?href="([^"]+)"', html, re.S):
            code, dt, title, href = m.groups()
            title = re.sub(r"<.*?>","",title).strip()
            rows.append((code, dt, title, ("https://kabutan.jp"+href) if href.startswith("/") else href))

        # 2) 旧UIフォールバック（リンクから4桁抽出）
        if not rows:
            for m in re.finditer(r'href="(/disclosures/[^"]+)".*?>(.+?)</a>', html, re.S):
                href, title = m.groups()
                title = re.sub(r"<.*?>","",title).strip()
                c = re.search(r'code=(\d{4})', href)
                if not c: 
                    c = re.search(r'/(\d{4})(?:[/?#]|$)', href)
                if c:
                    rows.append((c.group(1), "", title, "https://kabutan.jp"+href))

        if not rows:
            break

        with dst.open("a", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            for r in rows:
                w.writerow(r)

        total += len(rows)
        pno += 1
        if max_pages and pno > max_pages:
            break
        await page.wait_for_timeout(int(sleep*1000))

    await ctx.close()
    await browser.close()
    return total, pno-1

async def run(start: str, end: str, sleep: float, max_pages: int):
    d0 = date.fromisoformat(start); d1 = date.fromisoformat(end)
    async with async_playwright() as pw:
        cur = d0
        while cur <= d1:
            d = cur.isoformat()
            try:
                rows, pages = await fetch_day(pw, d, sleep=sleep, max_pages=max_pages)
                print(f"[crawl] {d} pages={pages} rows={rows} -> {out_csv_path(d)}")
            except Exception as e:
                print(f"[crawl][ERR] {d} {e}")
            cur += timedelta(days=1)

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--sleep", type=float, default=0.2)
    ap.add_argument("--max-pages", type=int, default=0)  # 0=全ページ
    a = ap.parse_args()
    asyncio.run(run(a.start, a.end, a.sleep, a.max_pages))
