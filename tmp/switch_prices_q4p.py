from pathlib import Path, re
y=Path("configs/tdnet_2014.yaml"); t=y.read_text(encoding="utf-8", errors="ignore")
import re
nl="  prices: data/proc/prices/jp_prices_std_compat_q4p.parquet"
t2=re.sub(r'(?m)^\s*prices\s*:.*$', nl, t) if re.search(r'(?m)^\s*prices\s*:', t) else t.rstrip()+"\npaths:\n"+nl+"\n"
Path("configs/tdnet_2014.yaml.bak_prices").write_text(t, encoding="utf-8"); y.write_text(t2, encoding="utf-8")
print({"patched":True})
