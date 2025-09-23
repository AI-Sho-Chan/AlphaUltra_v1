from pathlib import Path, re
f = Path("scripts/model_lightgbm_v2.py")
s = f.read_text(encoding="utf-8")

# 1) ログ出力を強制（起動直後にファイルへ）
s = s.replace(
    "def main():",
    "def main():\n    import logging, pathlib, os\n"
    "    pathlib.Path('reports').mkdir(exist_ok=True)\n"
    "    logging.basicConfig(filename='reports/model_lightgbm_v2.log', level=logging.INFO, "
    "format='%(asctime)s %(levelname)s %(message)s')\n"
    "    logging.info('[MARK] start')\n"
)

# 2) event_aggregates をスモーク時はno-opに
s = s.replace(
    "def event_aggregates(",
    "def event_aggregates("
).replace(
    "def event_aggregates(df",
    "def event_aggregates(df"
)

# 既存定義の直後に早期returnを注入
s = s.replace(
    "def event_aggregates(df",
    "def event_aggregates(df"
    ):
        if os.getenv('ALGO_SMOKE','0')=='1':
            # スモーク: 前処理スキップして df をそのまま返す
            return df
"
)

# 3) add_price_features/ensure_liquidity_cols の入口でもマーカー
s = s.replace("def add_price_features(", "def add_price_features(\n":)
s = s.replace("def ensure_liquidity_cols(", "def ensure_liquidity_cols(\n":)

# 保存
Path('scripts/model_lightgbm_v2.py.bak_smoke').write_text(s, encoding='utf-8')
f.write_text(s, encoding='utf-8')
print({'patched': True})
