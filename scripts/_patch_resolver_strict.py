# -*- coding: utf-8 -*-
def _valid_code4(c):
    try:
        n=int(c); return 1300<=n<=9999
    except: return False

def resolve_code_from_detail(sess, href):
    """詳細ページから 4桁株式コードを厳密抽出"""
    import re
    from bs4 import BeautifulSoup
    url = "https://kabutan.jp"+href if href.startswith("/") else href
    html = get_html(sess, url)
    if not html: return None
    soup = BeautifulSoup(html, "lxml")

    # 1) ラベル優先（例：証券コード/銘柄コード/コード）
    txt = soup.get_text(" ", strip=True)
    m = re.search(r"(?:証券コード|銘柄コード|コード)\D{0,6}(\d{4})", txt)
    if m and _valid_code4(m.group(1)): 
        return m.group(1)

    # 2) /stock/?code=#### のリンク（範囲チェック）
    for a in soup.select('a[href*="/stock/?code="]'):
        href2 = a.get("href") or ""
        m2 = re.search(r"/stock/\?code=(\d{4})", href2)
        if m2 and _valid_code4(m2.group(1)):
            return m2.group(1)

    # 3) 最後の保険：テキスト中の4桁（範囲チェック）
    for c in re.findall(r"(?<!\d)(\d{4})(?!\d)", txt):
        if _valid_code4(c): 
            return c
    return None
