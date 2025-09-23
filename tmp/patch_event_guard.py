from pathlib import Path, re
f = Path("scripts/model_lightgbm_v2.py")
src = f.read_text(encoding="utf-8")

# デコレータ/型ヒント/改行に強い検出
pat = re.compile(r'(?m)^(?:@\w[^\n]*\n)*def\s+event_aggregates\s*\([^\n]*\):\s*$')
m = pat.search(src)
if not m:
    # 緩め探索（関数名位置を見つけ、直後の改行に挿入）
    idx = src.find("def event_aggregates")
    if idx < 0:
        raise SystemExit({"error":"event_aggregates not found"})
    # 関数ヘッダ終了のコロンを探す
    colon = src.find(":", idx)
    if colon < 0: raise SystemExit({"error":"header colon not found"})
    # 次行の先頭インデントを測る
    nl = src.find("\n", colon)
    if nl < 0: nl = colon
    body_start = nl + 1
    indent = re.match(r'[ \t]*', src[body_start:]).group(0) or "    "
    guard = f"\n{indent}import os\n{indent}if os.environ.get('ALGO_SMOKE','0')=='1':\n{indent}    return df\n"
    out = src[:body_start] + guard + src[body_start:]
else:
    # マッチ直後の1行目インデントを取得
    body_start = m.end()
    # 次行のインデント
    import io
    s = io.StringIO(src[body_start:])
    first = s.readline()
    import re as _re
    indent = _re.match(r'[ \t]*', first).group(0) or "    "
    guard = f"\n{indent}import os\n{indent}if os.environ.get('ALGO_SMOKE','0')=='1':\n{indent}    return df\n"
    out = src[:body_start] + guard + src[body_start:]

Path("scripts/model_lightgbm_v2.py.bak_event").write_text(src, encoding="utf-8")
f.write_text(out, encoding="utf-8")
print({"patched": True})
