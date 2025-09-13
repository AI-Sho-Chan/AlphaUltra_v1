#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, csv, time, random, re
from pathlib import Path
import requests as rq
from bs4 import BeautifulSoup

# Fixed output roots per spec
BASE = Path(r"C:\AI\AlphaUltra_v1\data\raw\kabutan")
DBG  = Path(r"C:\AI\AlphaUltra_v1\reports\debug")
BASE.mkdir(parents=True, exist_ok=True)
DBG.mkdir(parents=True, exist_ok=True)


def build_session():
    ck = os.environ.get("KABUTAN_COOKIE", "").strip()
    if not ck:
        raise SystemExit("[crawl] KABUTAN_COOKIE not set")
    s = rq.Session()
    s.headers.update({
        "User-Agent": "alphaai-kabutan-crawler",
        "Accept-Language": "ja-JP",
        "Referer": "https://kabutan.jp/",
    })
    for kv in ck.split(";"):
        if "=" in kv:
            k, v = kv.strip().split("=", 1)
            s.cookies.set(k.strip(), v.strip(), domain="kabutan.jp", path="/")
    return s


def get_html(sess, url, tries=6, timeout=30):
    back = 1.0
    for _ in range(tries):
        r = sess.get(url, timeout=timeout)
        if r.status_code == 200:
            return r.text
        if r.status_code in (429, 503):
            time.sleep(back + random.uniform(0, 0.5))
            back = min(back * 2, 16)
            continue
        r.raise_for_status()
    return ""


def build_url_candidates(d: str, page: int):
    y, m, dd = d.split("-")
    ym = f"{y}{m}"
    return [
        ("date",   f"https://kabutan.jp/disclosures/?date={d}&page={page}"),
        ("ym_day", f"https://kabutan.jp/disclosures/?ym={ym}&day={dd}&page={page}"),
        ("ym",     f"https://kabutan.jp/disclosures/?ym={ym}&page={page}"),
    ]


def analyze_list_html(html: str, d: str) -> tuple[bool, int]:
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        return (False, 0)
    anchors = soup.select('a[href*="/disclosures/"]')
    cnt = len(anchors)
    has_d = False
    for t in soup.find_all("time"):
        txt = (t.get("datetime") or t.get_text(" ", strip=True) or "").strip()
        if d in txt:
            has_d = True
            break
    if not has_d:
        txt = soup.get_text(" ", strip=True)
        has_d = d in txt
    return ((cnt >= 20) and has_d, cnt)


def pick_working_url(sess, d: str, page: int = 1):
    for name, url in build_url_candidates(d, page):
        html = get_html(sess, url)
        ok, _ = analyze_list_html(html, d)
        if ok:
            def builder(p):
                for nm, u in build_url_candidates(d, p):
                    if nm == name:
                        return u
                return build_url_candidates(d, p)[0][1]
            return name, builder
    return "date", (lambda p: f"https://kabutan.jp/disclosures/?date={d}&page={p}")


def resolve_code_from_detail(sess, href, tries=3, timeout=10):
    """Resolve 4-digit code from detail page.
    - Prefer /stock/?code=#### link
    - Fallback to last 4 consecutive digits in page text
    Returns: (code4 or None, attempts, elapsed_sec)
    """
    url = "https://kabutan.jp" + href if href.startswith("/") else href
    attempts = 0
    back = 0.5
    start_t = time.time()
    html = ""
    for i in range(tries):
        attempts = i + 1
        try:
            r = sess.get(url, timeout=timeout)
            if r.status_code == 200:
                html = r.text
                break
            if r.status_code in (429, 503):
                time.sleep(max(0.0, back + random.uniform(-0.5, 0.5)))
                back = min(back * 2, 8)
                continue
            r.raise_for_status()
        except Exception:
            time.sleep(max(0.0, back + random.uniform(-0.5, 0.5)))
            back = min(back * 2, 8)
            continue
    elapsed = time.time() - start_t
    if not html:
        return (None, attempts, elapsed)
    m = re.search(r"/stock/\?code=(\d{4})", html)
    if m:
        return (m.group(1), attempts, elapsed)
    m2 = re.findall(r"(?<!\d)(\d{4})(?!\d)", BeautifulSoup(html, "lxml").get_text(" ", strip=True))
    if m2:
        return (m2[-1], attempts, elapsed)
    return (None, attempts, elapsed)


def parse_rows_primary(soup: BeautifulSoup):
    """Primary parse from list page, supporting new and old templates.
    Returns list of tuples: (code?, dt?, title, href)
    - New UI: [data-code] container
    - Old UI: anchors to /disclosures/, exclude nav words, title length > 3
      Also parse tabular form: td[0]=code, td[1]=datetime, td[2] a=title
    """
    rows = []
    ban = {"前へ", "次へ", "トップ", "ページ", "戻る"}

    def is_valid_code4(x: str) -> bool:
        if not (x and x.isdigit() and len(x) == 4):
            return False
        try:
            return int(x) >= 1300
        except Exception:
            return False

    # New UI
    for c in soup.select("[data-code]"):
        code = (c.get("data-code") or "").strip()
        a = c.select_one('a[href*="/disclosures/"]')
        title = (a.get_text(strip=True) if a else "").strip()
        href = (a.get("href") or "").strip() if a else ""
        t = c.find("time")
        dt = t.get("datetime") if (t and t.has_attr("datetime")) else ""
        if is_valid_code4(code) and len(title) > 3 and href:
            rows.append((code, dt, title, href))
    if rows:
        return rows

    # Old UI - anchors
    picked = set()
    for a in soup.select('a[href*="/disclosures/"]'):
        href = (a.get("href") or "").strip()
        title = (a.get_text(strip=True) or "").strip()
        if not href or len(title) <= 3 or any(b in title for b in ban):
            continue
        dt = ""
        tr = a.find_parent("tr")
        if tr:
            tds = tr.find_all("td")
            if len(tds) >= 2:
                cand = tds[1].get_text(strip=True)
                if re.search(r"\d{4}-\d{2}-\d{2}", cand) or "年" in cand:
                    dt = cand
        sig = (dt, title, href)
        if sig in picked:
            continue
        picked.add(sig)
        rows.append(("", dt, title, href))

    # Old UI - table rows (code, dt, title)
    for tr in soup.select("tr"):
        tds = tr.find_all("td")
        if len(tds) < 3:
            continue
        code = tds[0].get_text(strip=True)
        dt = tds[1].get_text(strip=True)
        a = tds[2].find('a', href=re.compile(r"/disclosures/"))
        if not a:
            continue
        title = a.get_text(strip=True)
        href = (a.get("href") or "").strip()
        if not href or len(title) <= 3 or any(b in title for b in ban):
            continue
        if code and is_valid_code4(code):
            rows.append((code, dt, title, href))
        else:
            rows.append(("", dt, title, href))

    return rows


def _safe_append_csv(dst_path: Path, rows, max_tries=6):
    """Atomic, retrying CSV append that survives read-only/locks.
    Writes existing + new rows to a temp file, then os.replace.
    Exponential backoff: 0.5 -> 1 -> 2 -> 4 -> 8s with ±0.5s jitter.
    Returns True on success, False on give-up.
    """
    dst = Path(dst_path)
    tmp = dst.with_suffix(".csv.tmp")
    back = 0.5
    for _ in range(max_tries):
        try:
            if dst.exists():
                os.chmod(dst, 0o666)
        except Exception:
            pass
        try:
            existing = ""
            if dst.exists():
                try:
                    with dst.open("r", encoding="utf-8-sig", newline="") as rf:
                        existing = rf.read()
                except Exception:
                    existing = ""
            with tmp.open("w", encoding="utf-8-sig", newline="") as wf:
                if existing:
                    wf.write(existing)
                    if not existing.endswith("\n"):
                        wf.write("\n")
                writer = csv.writer(wf)
                if rows:
                    writer.writerows(rows)
            os.replace(tmp, dst)
            return True
        except PermissionError:
            try:
                if tmp.exists():
                    tmp.unlink(missing_ok=True)
            except Exception:
                pass
            time.sleep(max(0.0, min(back, 8) + random.uniform(-0.5, 0.5)))
            back = min(back * 2, 8)
            continue
        except Exception:
            try:
                if tmp.exists():
                    tmp.unlink(missing_ok=True)
            except Exception:
                pass
            time.sleep(max(0.0, min(back, 8) + random.uniform(-0.5, 0.5)))
            back = min(back * 2, 8)
            continue
    try:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
    except Exception:
        pass
    return False


def crawl_day(d: str, sleep=0.25, max_pages=0, max_items_per_day=0):
    s = build_session()
    outdir = BASE / d
    outdir.mkdir(parents=True, exist_ok=True)
    dst = outdir / "tdnet.csv"
    if not dst.exists():
        with dst.open("w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f).writerow(["code", "time", "title", "URL"])

    page = 1
    empty = 0
    detail_calls = 0
    detail_tries_total = 0
    detail_elapsed_total = 0.0
    day_resolved_total = 0

    tpl_name, url_builder = pick_working_url(s, d, page=1)
    print(f"[url] {d} template={tpl_name}")

    while True:
        list_url = url_builder(page)
        html = get_html(s, list_url)
        if not html:
            (DBG / f"kabutan_{d}_p{page}.html").write_text("", encoding="utf-8")
            break
        soup = BeautifulSoup(html, "lxml")
        prim = parse_rows_primary(soup)
        if not prim:
            (DBG / f"kabutan_{d}_p{page}.html").write_text(html, encoding="utf-8")
            empty += 1
            if empty >= 2:
                break
            page += 1
            time.sleep(sleep)
            continue

        resolved = []
        for code, dt, title, href in prim:
            c4 = code
            if not (c4 and c4.isdigit() and len(c4) == 4 and int(c4) >= 1300):
                c4, tr, elapsed = resolve_code_from_detail(s, href)
                detail_calls += 1
                detail_tries_total += tr
                detail_elapsed_total += elapsed
                c4 = c4 or ""
            if not (c4 and c4.isdigit() and len(c4) == 4 and int(c4) >= 1300):
                continue
            url = "https://kabutan.jp" + href if href.startswith("/") else href
            resolved.append((c4, dt, title, url))

        print(f"[fetch] {d} p{page} prim={len(prim)} resolved={len(resolved)}")

        if not resolved:
            (DBG / f"kabutan_{d}_p{page}.html").write_text(html, encoding="utf-8")
            empty += 1
            if empty >= 2:
                break
            page += 1
            time.sleep(sleep)
            continue

        ok = _safe_append_csv(dst, resolved)
        if not ok:
            print(f"[warn] append failed after retries: {dst}")

        day_resolved_total += len(resolved)
        empty = 0
        page += 1
        if max_pages and page > max_pages:
            break
        if max_items_per_day and day_resolved_total >= max_items_per_day:
            break
        time.sleep(sleep)

    rows_written = max(0, sum(1 for _ in open(dst, encoding="utf-8-sig")) - 1)
    print(f"[kabu_crawl] {d} pages~{page-1} rows_total={rows_written} -> {dst}")
    if detail_calls:
        avg = detail_elapsed_total / detail_calls if detail_calls else 0.0
        print(f"[detail] tries_total={detail_tries_total} calls={detail_calls} avg_time={avg:.3f}s")


if __name__ == "__main__":
    import argparse
    from datetime import date, timedelta
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--sleep", type=float, default=0.25)
    ap.add_argument("--max-pages", type=int, default=0)
    ap.add_argument("--max-items-per-day", type=int, default=0)
    a = ap.parse_args()
    cur = date.fromisoformat(a.start)
    end = date.fromisoformat(a.end)
    while cur <= end:
        d = cur.isoformat()
        crawl_day(d, a.sleep, a.max_pages, a.max_items_per_day)
        cur += timedelta(days=1)

