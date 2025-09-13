import re, pathlib, sys
targets = [pathlib.Path(p) for p in [
  'tools/tdnet_kabutan_crawl_range.py',
  'tools/tdnet_kabutan_fetch_html.py',
  'tools/tdnet_kabutan_enrich_day.py']]
for p in targets:
    if not p.exists(): 
        print('skip', p); 
        continue
    b = p.read_bytes()
    for enc in ('cp932','utf-8','utf-8-sig'):
        try:
            s = b.decode(enc); break
        except: pass
    else:
        s = b.decode('utf-8','ignore')
    # 三連引用を丸ごと落とす（未終端でも末尾まで落とす）
    s = re.sub(r'(?s)\"\"\".*?\"\"\"','', s)
    s = re.sub(r"(?s)'''.*?'''",'', s)
    # 制御文字除去
    s = re.sub(r'[\x00-\x08\x0b-\x1f]',' ', s)
    p.write_text(s, encoding='utf-8')
print('fixed')
