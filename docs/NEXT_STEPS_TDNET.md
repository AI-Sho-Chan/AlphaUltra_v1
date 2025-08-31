# NEXT_STEPS_TDNET（T0–T7 実行SOP）

> 共有は「コミットSHA＋対象ログ末尾20行＋成果物存在チェック3行」。

## T0 準備
- この4文書を `docs/` に配置。`reports/checks/handoff_status.json` を作成。

## T1 TDNET取込
- 入力：株探エクスポート（CSV/JSON/TSVいずれか）
- 保存：`data/raw/tdnet/YYYY/MM/DD/<code>.json`（UTF‑8）に正規化。
- 成果物：日あたり10件以上。失敗0。
- 参考スクリプト：`scripts/tdnet_ingest.py`

## T2 特徴化（TDNET）
- 分類・極性・強度・新規性・時刻ゲート。
- 出力：`data/proc/features_tdnet/tdnet_event_features.parquet`

## T3 定量特徴
- モメンタム、ボラ、β、IdioVol、残差モメンタム。
- 出力：`data/proc/features_quant.parquet`

## T4 ラベル
- y_2x / y_10x / 相対（1M/3M/12M）を T+1基準で定義。
- 出力：`data/proc/labels/targets.parquet`

## T5 結合
- `asof forward`（T+1寄り）で `dataset_final.parquet`。重複なし。欠損<1%。

## T6 検証
- Purged/Embargo CV＋クラスタPurge、Walk‑Forward、コスト控除、**DSR**。
- 指標：AUC‑ROC/PR、P@K、ネットSharpe、到達日数分布。

## T7 校正・閾値
- OOF→**Isotonic**→**PPV‑Coverage**で θ*（PPV≥80%）を決定。
- 出力：`configs/thresholds.yaml`、`reports/checks/ppv_curve_*.csv`