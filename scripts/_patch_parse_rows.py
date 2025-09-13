# -*- coding: utf-8 -*-
def parse_rows(html: str):
    import re
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    rows = []
    ban  = {"前へ","次へ","トップ","ページ","戻る"}

    # 1) 新UI: data-code カード（あれば最優先）
    for c in soup.select("[data-code]"):
        code=(c.get("data-code") or "").strip()
        a=c.select_one('a[href*="/disclosures/"]')
        title=(a.get_text(strip=True) if a else "").strip()
        href=(a.get("href") or "").strip() if a else ""
        t=c.find("time"); dt=t.get("datetime") if (t and t.has_attr("datetime")) else ""
        if code.isdigit() and len(code)==4 and len(title)>3 and href:
            url="https://kabutan.jp"+href if href.startswith("/") else href
            rows.append((code,dt,title,url))
    if rows: 
        return rows

    # 2) 旧UI: 「/disclosures/…」リンクを基準に、同じ行/同じli内の「/stock/?code=####」から code を補完
    def find_code_near(node):
        # 兄弟/親の a に /stock/?code=#### がいればそれを採用
        for a2 in node.find_all("a", href=True):
            m=re.search(r"/stock/\?code=(\d{4})", a2["href"])
            if m: return m.group(1)
        # 同じtr内（td[0]）に4桁があれば採用
        tr=node.find_parent("tr")
        if tr:
            tds=tr.find_all("td")
            if tds:
                m=re.search(r"(?<!\d)(\d{4})(?!\d)", tds[0].get_text(" ", strip=True))
                if m: return m.group(1)
        # テキスト全体から最後の4桁を拾う
        m=re.findall(r"(?<!\d)(\d{4})(?!\d)", node.get_text(" ", strip=True))
        if m: return m[-1]
        return None

    picked=set()
    for a in soup.select('a[href*="/disclosures/"]'):
        href=(a.get("href") or "").strip()
        if not href or any(b in (a.get_text(strip=True) or "") for b in ban):
            continue
        code=find_code_near(a.parent or a)
        if not (code and code.isdigit() and len(code)==4):
            continue
        title=(a.get_text(strip=True) or "").strip()
        if len(title)<=3: 
            continue
        # 近傍の time / 日付
        dt=""
        t=a.find_parent().find("time") if a.find_parent() else None
        if t and t.has_attr("datetime"): dt=t["datetime"]
        if not dt:
            # 親行/親liのテキストに日付らしきものがあれば採用
            cont=(a.find_parent("tr") or a.find_parent("li") or a.parent)
            if cont:
                cand=cont.get_text(" ", strip=True)
                if re.search(r"\d{4}-\d{2}-\d{2}", cand) or "年" in cand:
                    dt=cand
        url="https://kabutan.jp"+href if href.startswith("/") else href
        sig=(code,dt,title,url)
        if sig in picked: 
            continue
        rows.append(sig); picked.add(sig)

    # 3) 最後の保険: テーブル行（td[0]=コード, td[2] a=タイトル, td[1]=日時）
    if not rows:
        for tr in soup.select("table tr"):
            tds=tr.find_all("td")
            if len(tds)<3: 
                continue
            a=tds[2].find("a", href=True)
            if not a: 
                continue
            href=a["href"]
            title=(a.get_text(strip=True) or "").strip()
            if len(title)<=3 or any(b in title for b in ban):
                continue
            code_txt=(tds[0].get_text(strip=True) or "")
            m=re.search(r"(?<!\d)(\d{4})(?!\d)", code_txt)
            if not m: 
                continue
            code=m.group(1)
            dt=tds[1].get_text(strip=True)
            if not (re.search(r"\d{4}-\d{2}-\d{2}", dt) or "年" in dt): dt=""
            url="https://kabutan.jp"+href if href.startswith("/") else href
            rows.append((code,dt,title,url))
    return rows
