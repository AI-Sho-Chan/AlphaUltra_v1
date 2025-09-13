# -*- coding: utf-8 -*-
import codecs, glob, json
files = glob.glob(r"data/raw/kabutan/2014-*/tdnet.csv")
header_only = [f for f in files if sum(1 for _ in codecs.open(f,"r","utf-8-sig")) <= 1]
print(json.dumps({
  "days_total": len(files),
  "days_header_only": len(header_only),
  "sample": header_only[:5]
}, ensure_ascii=False))
