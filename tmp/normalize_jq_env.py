# jq.env を正規化：BOM除去＋refreshToken を1行に
import re, pathlib, sys
p = pathlib.Path(".secrets/jq.env")
t = p.read_bytes()
# BOM(239 187 191)除去
if t[:3] == b"\xef\xbb\xbf": t = t[3:]
s = t.decode("utf-8", errors="ignore")

# refreshToken= 以降の値を改行や空白を除去して1行化
m = re.search(r"refreshToken\s*=\s*(.+)", s, flags=re.I|re.S)
if not m:
    print({"ok":False,"reason":"refreshToken= not found"}); sys.exit(1)
val = m.group(1)
# 次のキーが来る前までに限定（念のため）
val = re.split(r"\n[A-Za-z_]+\s*=", val, maxsplit=1)[0]
# 空白・改行を全削除
val = re.sub(r"\s+", "", val)
new = f"refreshToken={val}\n"
pathlib.Path(".secrets/jq.env").write_text(new, encoding="utf-8")
print({"ok":True,"len":len(val)})
