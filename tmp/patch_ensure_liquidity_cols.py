from pathlib import Path

f = Path("scripts/model_lightgbm_v2.py")
src = f.read_text(encoding="utf-8")

lines = src.splitlines()
out = []
i = 0
inserted = False

snippet = [
"    # === harden columns ===",
"    if \"adj_close\" not in px.columns:",
"        for c in (\"adj_close\",\"px_close\",\"close\",\"Adj Close\",\"adjclose\"):",
"            if c in px.columns:",
"                if c != \"adj_close\": px[\"adj_close\"] = px[c]",
"                break",
"        else:",
"            raise KeyError(\"adj_close missing; cols=\"+str(list(px.columns)[:30]))",
"    if \"volume\" not in px.columns:",
"        for v in (\"volume\",\"vol\",\"Volume\",\"volume_adj\"):",
"            if v in px.columns:",
"                if v != \"volume\": px[\"volume\"] = px[v]",
"                break",
"    # === end harden ===",
]

while i < len(lines):
    out.append(lines[i])
    if lines[i].startswith("def ensure_liquidity_cols("):
        # 次行が関数ボディ開始
        i += 1
        out.append(lines[i])
        # ここでスニペット挿入
        out.extend(snippet)
        inserted = True
    i += 1

if not inserted:
    raise SystemExit({"error":"ensure_liquidity_cols not found"})

bak = f.with_suffix(".py.bak")
bak.write_text(src, encoding="utf-8")
f.write_text("\n".join(out), encoding="utf-8")
print({"patched": True, "backup": str(bak)})
