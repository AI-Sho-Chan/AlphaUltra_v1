from pathlib import Path
import re, json

# 1) 選定結果の読み込み
meta = json.loads(Path("tmp/chosen_prices.json").read_text(encoding="utf-8"))
p = meta["chosen"].replace("\\", "/")  # YAMLでは/に統一
y = Path("configs/tdnet_2014.yaml")

# 2) YAML読み込み
txt = y.read_text(encoding="utf-8", errors="ignore")

# 3) prices: の行を用意（paths:配下想定のインデント2スペース）
new_line = f"  prices: {p}"

if re.search(r'(?m)^\s*prices\s*:', txt):
    # 既存のprices行を置換（インデントを維持しない方針で確実に上書き）
    txt2 = re.sub(r'(?m)^\s*prices\s*:.*$', new_line, txt)
elif re.search(r'(?m)^\s*paths\s*:\s*$', txt):
    # paths: の直後に差し込み（次の非空行の直前でも可だが簡潔に直後）
    txt2 = re.sub(r'(?m)^(paths\s*:\s*)$', r"\1\n"+new_line, txt)
else:
    # paths: が無ければ新設
    txt2 = txt.rstrip() + "\npaths:\n" + new_line + "\n"

# 4) 書き戻し（バックアップ生成）
bak = y.with_suffix(".yaml.bak")
bak.write_text(txt, encoding="utf-8")
y.write_text(txt2, encoding="utf-8")

print({"patched": True, "prices": p, "backup": str(bak)})
