# scripts/set_prices_in_config.py
import json, yaml
from pathlib import Path

p=Path("configs/tdnet_2014.yaml")
cfg = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
cfg.setdefault("paths",{})["prices"] = "data/proc/prices/jp_prices_std.parquet"  # ← T6が読むキー
ds = dict(cfg.get("dataset") or {})
ds.setdefault("join","inner")            # まずは既定（events基準の内積）
ds.setdefault("events_only", True)       # 2014Q4はイベント起点でOK
cfg["dataset"]=ds

p.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")
print(json.dumps({"paths":cfg["paths"],"dataset":cfg["dataset"]}, ensure_ascii=False))
