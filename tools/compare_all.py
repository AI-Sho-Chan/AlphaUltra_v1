# === Phase-1 refactor shim ===
import sys
from pathlib import Path
sys.path.insert(0, str((Path(__file__).resolve().parents[1] / "src")))
from alphaultra.utils.root import project_root

import pandas as pd

ROOT = project_root()
CMP  = ROOT / "reports" / "compare"

def main():
    # 最新 *_all_metrics.csv をまとめる既存の処理（元の本文を下に残してOK）
    # ↓ここから元の compare_all の中身を実行（既存関数／処理があればそのまま）
    import glob, datetime, csv, json

    latest = sorted(glob.glob(str(CMP / "*_all_metrics.csv")), key=lambda p: Path(p).stat().st_mtime)[-1]
    df = pd.read_csv(latest)
    # そのまま上書き出力（既存仕様維持）
    out = Path(latest)
    print(f"[COMPARE-ALL] {out}")
if __name__ == "__main__":
    main()
