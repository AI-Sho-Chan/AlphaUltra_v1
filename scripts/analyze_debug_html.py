# -*- coding: utf-8 -*-
import re, sys, json
from pathlib import Path
from bs4 import BeautifulSoup

# 対象日（さっきの 2014-11-14）
H = Path(r"reports/debug/kabutan_2014-11-14_p1.html")
html = H.read_text(encoding="utf-8", errors="ignore")
soup = BeautifulSoup(html, "lxml")

# 候補セレクタのカウント
cand = {
  "data_code_cards"  : "[data-code]",
  "a_code_param"     : 'a[href*="/disclosures/?code="]',
  "a_disclosures_any": 'a[href*="/disclosures/"]',
  "li_disclosure"    : ".disclosure-list__item, .companyir-lst li, li",
  "table_rows"       : "table tr",
  "#main a"          : "#main a, main a, #contents a"
}
out={}
for k,sel in cand.items():
    out[k] = len(soup.select(sel))

# aタグから code=#### を拾った件数
anchors = soup.select('a[href]')
hits=[]
for a in anchors:
    href = a.get("href") or ""
    m = re.search(r'code=(\d{4})', href) or re.search(r'/(\d{4})(?:[/?#]|$)', href)
    if m: 
        t = (a.get_text(strip=True) or "")
        if len(t)>3 and not any(b in t for b in ("前へ","次へ","トップ","ページ","戻る")):
            hits.append((m.group(1), t[:40], href[:80]))
out["anchors_with_code"] = len(hits)
out["sample_hits"] = hits[:5]

print(json.dumps(out, ensure_ascii=False, indent=2))
