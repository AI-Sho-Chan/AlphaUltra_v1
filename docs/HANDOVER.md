# HANDOVER / 引き継ぎ要点

1) 目的KPI3アルゴ: `docs/PROJECT_CHARTER.md`
2) いま動いているもの: 夜間 `run_fin_backfill.ps1`（単一、429クールダウン）
3) 自動: しきい値で finfeaturesT5T6T7
4) 主要パス:
   - features: `data/proc/features_tdnet/tdnet_event_features.parquet`
   - prices:   `data/proc/prices/jp_prices_std.parquet`
   - panel:    `data/proc/dataset/tdnet_panel_{real|full}.parquet`
   - model:    `reports/checks/tdnet_model_y_2x*.{json,parquet}`, `reports/*log`
5) 詰まり:
   - 429/no_token  待つ＆単一プロセス厳守
   - AUC=null  Q4陽性不足、バックフィル継続で解消
6) 次手:
   - 訓練窓を 20112012 へ拡大、log/比率/イベント集約拡充、グリッド幅拡大
