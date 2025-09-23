import os, requests, pandas as pd, numpy as np, pathlib
tok = open(".secrets/jq_id_token.txt",encoding="utf-8").read().strip()
H = {"Authorization": f"Bearer {tok}"}
# 例：銘柄コードと日付の組を1件だけ試す（必要に応じて置換）
code, date = "1301", "2014-12-26"  # サンプル
urls = [
  # 実在のIR/決算サマリ系に置換してください
  # f"https://api.jpx-jquants.com/v1/ir/summary?code={code}&date={date}",
]
rows=[]
for u in urls:
    try:
        r = requests.get(u, headers=H, timeout=15)
        if r.status_code==200:
            js = r.json()
            rows.append({"ticker":code,"asof":date,
                         "eps_yoy": js.get("eps_yoy"),
                         "rev_yoy": js.get("rev_yoy"),
                         "op_yoy":  js.get("op_yoy")})
            break
    except: pass

if rows:
    pd.DataFrame(rows).to_parquet("tmp/jq_asof_sample.parquet", index=False)
print({"ok":bool(rows),"file":"tmp/jq_asof_sample.parquet" if rows else "none"})
