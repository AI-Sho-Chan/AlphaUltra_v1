from pathlib import Path, re
y = Path("configs/tdnet_2014.yaml")
txt = y.read_text(encoding="utf-8", errors="ignore")
p = "data/proc/prices/jp_prices_std_compat_slim_q4.parquet"
new_line = f"  prices: {p}"
import re
if re.search(r'(?m)^\s*prices\s*:', txt):
    txt2 = re.sub(r'(?m)^\s*prices\s*:.*$', new_line, txt)
elif re.search(r'(?m)^\s*paths\s*:\s*$', txt):
    txt2 = re.sub(r'(?m)^(paths\s*:\s*)$', r"\1\n"+new_line, txt)
else:
    txt2 = txt.rstrip()+"\npaths:\n"+new_line+"\n"
Path("configs/tdnet_2014.yaml.bak_fix").write_text(txt, encoding="utf-8")
y.write_text(txt2, encoding="utf-8")
print({"patched": True, "prices": p})
