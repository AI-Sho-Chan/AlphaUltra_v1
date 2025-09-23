from pathlib import Path
import io,re

f = Path("scripts/model_lightgbm_v2.py")
src = f.read_text(encoding="utf-8")

# def event_aggregates(...) の先頭行を特定
m = re.search(r'(?m)^def\s+event_aggregates\s*\((.*?)\):\s*$', src)
if not m:
    raise SystemExit({"error":"event_aggregates not found"})

start = m.end()
# 次行のインデントを取得（通常は4スペース）
lines = src[start:].splitlines()
if not lines: raise SystemExit({"error":"function body not found"})
indent = re.match(r'^(\s*)', lines[0]).group(1) or "    "

guard = (
    "\n" + indent + "import os\n" +
    indent + "if os.environ.get('ALGO_SMOKE','0')=='1':\n" +
    indent + "    return df\n"
)

patched = src[:start] + guard + src[start:]
Path("scripts/model_lightgbm_v2.py.bak_event").write_text(src, encoding="utf-8")
f.write_text(patched, encoding="utf-8")
print({'patched': True})
