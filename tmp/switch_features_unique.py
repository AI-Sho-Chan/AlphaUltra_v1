from pathlib import Path, re
y = Path("configs/tdnet_2014.yaml")
txt = y.read_text(encoding="utf-8", errors="ignore")
new_line = "  features: tmp/features_tdnet_q4_intersect_unique.parquet"
import re
if re.search(r'(?m)^\s*features\s*:', txt):
    txt2 = re.sub(r'(?m)^\s*features\s*:.*$', new_line, txt)
elif re.search(r'(?m)^\s*paths\s*:\s*$', txt):
    txt2 = re.sub(r'(?m)^(paths\s*:\s*)$', r"\1\n"+new_line, txt)
else:
    txt2 = txt.rstrip()+"\npaths:\n"+new_line+"\n"
Path("configs/tdnet_2014.yaml.bak_feat2").write_text(txt, encoding="utf-8")
y.write_text(txt2, encoding="utf-8")
print({"patched": True})
