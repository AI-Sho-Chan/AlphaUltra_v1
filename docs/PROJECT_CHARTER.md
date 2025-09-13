# Project Charter（目的 / KPI / 3アルゴ目標）

## 目的
- TDNET × 価格 × 財務を統合し、イベントドリブンの日本株アルファを検証・運用可能な形で整備。

## KPI（Phase-1）
- データ基盤
  - Kabutan→JSON（2014）: ≥ 5万行 …達成
  - 価格 REAL（2014）: coverage ≥ 0.95 & rows ≥ 500 …達成
  - 財務（J-Quants 四半期）: fin_ok > 100 …達成
- 検証基盤
  - T5: Purged/Embargo WF 分割のJSONを安定生成（Q4テスト固定・2012〜学習）…稼働
  - T6: LGBM OOF AUC-ROC ≥ 0.60（目標）…未達（データ増で継続改善）
  - T7: PPV≥0.8 のしきい値算出 …継続算出（データ増で安定化）

## 3つのアルゴ目標（T5/T6/T7）
- T5: 時系列CV（Purged=20D, Embargo=5D, ClusterPurge=60D相関, Q4/2014を真のOOSテスト）
- T6: LGBMベースライン（--use-featuresで財務/価格/イベント集約を注入、グリッド＋不均衡対応）
- T7: Isotonic校正（PPV-Coverage曲線から PPV≥0.8 の最小スコア thr_ppv80 を出力）

## 現状（スナップショット）
- バックフィル：J-Quants四半期財務が継続増加（fail_reasonsのno_tokenは収束）
- as-of財務（正規化）：rows増・tickers増（すでに2,000+銘柄規模→直近で~2,900+銘柄到達）
- 学習：AUCは0.18〜0.56のレンジで推移（データ増分ごとに再学習し改善探索）
