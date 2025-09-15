# scripts/ensure_prices_in_config.py
import json, yaml
from pathlib import Path
p=Path("configs/tdnet_2014.yaml")
cfg=yaml.safe_load(p.read_text(encoding="utf-8")) or {}
cfg.setdefault("paths",{})["adj_prices"]="data/proc/adj_prices/adj_prices.parquet"
ds=dict(cfg.get("dataset") or {})
ds.setdefault("join","left"); ds.setdefault("events_only",False)
cfg["dataset"]=ds
p.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")
print(json.dumps({"paths":cfg["paths"],"dataset":cfg["dataset"]}, ensure_ascii=False))
