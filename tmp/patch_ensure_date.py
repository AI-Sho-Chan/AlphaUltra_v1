from pathlib import Path, re
f = Path("scripts/model_lightgbm_v2.py")
src = f.read_text(encoding="utf-8")

anchor = "    # === end pre-merge reduction ==="
inject = """
    # === ensure date column for downstream code ===
    if "date" not in px.columns and "eff_date" in px.columns:
        px["date"] = px["eff_date"]
    # === end date ensure ===
"""

if anchor not in src:
    raise SystemExit({"error":"anchor not found; apply near key normalization manually"})
patched = src.replace(anchor, anchor + inject)
bak = f.with_suffix(".py.bak_datefix")
bak.write_text(src, encoding="utf-8")
f.write_text(patched, encoding="utf-8")
print({"patched": True, "backup": str(bak)})
