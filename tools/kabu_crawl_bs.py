# -*- coding: utf-8 -*-
"""
Kabutan TDNET crawler (v3.1)
- 1日あたり page=1..N を全取得（空ページ2連続で終了）
- Cookieは requests.Session に安全設定（latin-1問題回避）
- 新UI([data-code] カード) と旧UI(表/リンク)を両対応
- CSVはUTF-8 SIG。0件でもヘッダを書き出す
- 0件ページは C:\AI\AlphaUltra_v1\reports\debug\kabutan_<YYYY-MM-DD>_p{n}.html に保存
- 出力先は v1 固定: C:\AI\AlphaUltra_v1\data\raw\kabutan\<date>\tdnet.csv
"""
import os, csv, time, random, re
from pathlib import Path
import requests as rq
from bs4 import BeautifulSoup

BASE = Path(r"C:\AI\AlphaUltra_v1\data\raw\kabutan")
DBG  = Path(r"C:\AI\AlphaUltra_v1\reports\debug")
BASE.mkdir(parents=True, exist_ok=True)
DBG.mkdir(parents=True, exist_ok=True)

def build_session() -> rq.Session:
    ck = os.environ.get("KABUTAN_COOKIE", "").strip()
    if not ck:
        raise SystemExit("[crawl] KABUTAN_COOKIE not set")
    s = rq.Session()
    s.headers.update({
        "User-Agent": "alphaai-kabutan-crawler",
        "Accept-Language": "ja-JP",
        "Referer": "https://kabutan.jp/"
    })
    # CookieはSessionへ設定（ヘッダ直入れ不可）
    for kv in ck.split(";"):
        if "=" in kv:
            k, v = kv.strip().split("=", 1)
            s.cookies.set(k.strip(), v.strip(), domain="kabutan.jp", path="/")
    return s

def fetch_html(sess: rq.Session, d: str, page: int, tries: int = 6) -> str:
    url = f"https://kabutan.jp/disclosures/?date={d}&page={page}"
    back = 1.0
    for _ in range(tries):
        r = sess.get(url, timeout=30)
        if r.status_code == 200:
            return r.text
        if r.status_code in (429, 503):
            time.sleep(back + random.uniform(0, 0.5))
            back = min(back * 2, 16)
            continue
        r.raise_for_status()
    return ""

def parse_rows(html: str):
    """returns list[tuple(code, dt, title, url)]"""
    soup = BeautifulSoup(html, "lxml")
    rows = []

    # 新UI: data-code カード
    for c in soup.select("[data-code]"):
        code = (c.get("data-code") or "").strip()
        a = c.select_one('a[href*="/disclosures/"]')
        title = (a.get_text(strip=True) if a else "").strip()
        href  = (a.get("href") or "").strip() if a else ""
        t = c.find("time")
        dt = t.get("datetime") if (t and t.has_attr("datetime")) else ""
        if code.isdigit() and len(code) == 4 and title:
            url = "https://kabutan.jp"+href if href.startswith("/") else href
            rows.append((code, dt, title, url))

    # 旧UI: リンク/表フォールバック
    if not rows:
        for a in soup.select('a[href*="/disclosures/?code="], a[href^="/disclosures/"]'):
            href = (a.get("href") or "")
            m = re.search(r'code=(\d{4})', href) or re.search(r'/(\d{4})(?:[/?#]|$)', href)
            if not m: 
                continue
            code = m.group(1)
            title = (a.get_text(strip=True) or "").strip()
            if code.isdigit() and len(code) == 4 and title:
                url = "https://kabutan.jp"+href if href.startswith("/") else href
                rows.append((code, "", title, url))
        if not rows:
            for tr in soup.select("table tr"):
                tds = tr.find_all("td")
                if len(tds) >= 3:
                    code_txt = (tds[0].get_text(strip=True) or "")
                    code = "".join(ch for ch in code_txt if ch.isdigit())[-4:]
                    a = tds[2].find("a")
                    title = (a.get_text(strip=True) if a else "").strip()
                    href = (a.get("href") or "").strip() if a else ""
                    if code.isdigit() and len(code) == 4 and title:
                        url = "https://kabutan.jp"+href if href.startswith("/") else href
                        dt = tds[1].get_text(strip=True)
                        rows.append((code, dt, title, url))
    return rows

def crawl_day(d: str, sleep: float = 0.25, max_pages: int = 0):
    sess = build_session()
    outdir = BASE / d
    outdir.mkdir(parents=True, exist_ok=True)
    dst = outdir / "tdnet.csv"
    # 0件でもCSVは必ず存在させる
    if not dst.exists():
        with dst.open("w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f).writerow(["コード", "掲載日時", "タイトル", "URL"])

    total = 0
    page = 1
    last_sig = None
    empty_streak = 0

    while True:
        html = fetch_html(sess, d, page)
        if not html:
            (DBG / f"kabutan_{d}_p{page}.html").write_text("", encoding="utf-8")
            break

        rows = parse_rows(html)
        if not rows:
            (DBG / f"kabutan_{d}_p{page}.html").write_text(html, encoding="utf-8")
            empty_streak += 1
            if empty_streak >= 2:
                break
            page += 1
            time.sleep(sleep)
            continue

        empty_streak = 0
        sig = rows[0]  # 最初の行で重複検知
        if sig == last_sig:
            break
        last_sig = sig

        with dst.open("a", newline="", encoding="utf-8-sig") as f:
            csv.writer(f).writerows(rows)
        total += len(rows)
        page += 1
        if max_pages and page > max_pages:
            break
        time.sleep(sleep)

    # 正しい累計行数を表示（ヘッダ除外）
    try:
        rows_written = max(0, sum(1 for _ in open(dst, encoding="utf-8-sig")) - 1)
    except Exception:
        rows_written = total
    print(f"[kabu_crawl] {d} pages~{page-1} rows_total={rows_written} -> {dst}")
    return rows_written, page - 1

if __name__ == "__main__":
    import argparse
    from datetime import date, timedelta
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True)
    ap.add_argument("--end",   required=True)
    ap.add_argument("--sleep", type=float, default=0.25)
    ap.add_argument("--max-pages", type=int, default=0)
    a = ap.parse_args()
    cur = date.fromisoformat(a.start); end = date.fromisoformat(a.end)
    while cur <= end:
        d = cur.isoformat()
        crawl_day(d, a.sleep, a.max_pages)
        cur += timedelta(days=1)
