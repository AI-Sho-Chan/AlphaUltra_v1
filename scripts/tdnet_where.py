# scripts/tdnet_where.py
from pathlib import Path
import json, re

CFG = Path("configs/paths_local.yaml")
def read_cfg():
    d = {"paths":{}, "scope":{}}
    if not CFG.exists(): return d
    for line in CFG.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*(tdnet_raw|tdnet_quarantine|kabutan_export|tdnet_start|tdnet_end)\s*:\s*(.+?)\s*$", line)
        if m:
            k,v = m.group(1), m.group(2)
            if k.startswith("tdnet_") or k=="kabutan_export":
                (d["paths"])[k] = v
            else:
                (d["scope"])[k] = v
    return d

cfg = read_cfg()
tdnet = Path(cfg["paths"].get("tdnet_raw","data/raw/tdnet"))
qtn   = Path(cfg["paths"].get("tdnet_quarantine","data/raw/tdnet_bak_scope"))
kab   = cfg["paths"].get("kabutan_export","")

# 軽量存在確認（重い全走査はしない）
exists = tdnet.exists()
s2013 = (tdnet/"2013").exists()
s2014 = (tdnet/"2014").exists()
sample = None
for pat in [(tdnet/"2013"/"09"), (tdnet/"2013"/"10"), (tdnet/"2014"/"01")]:
    if pat.exists():
        it = list(pat.glob("*/*.json"))[:1]
        if it:
            sample = str(it[0]); break

out = {
  "tdnet_raw": str(tdnet.resolve()),
  "exists": exists,
  "has_2013": s2013,
  "has_2014": s2014,
  "sample_json": sample,
  "tdnet_quarantine": str(qtn.resolve()),
  "kabutan_export": kab,
  "scope": cfg.get("scope",{})
}
print(json.dumps(out, ensure_ascii=False))
