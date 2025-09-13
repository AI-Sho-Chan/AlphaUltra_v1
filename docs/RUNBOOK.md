# RUNBOOK — 運用手順

## 夜間バックフィル（J-Quants 四半期財務）
- 実行: `scripts\run_fin_backfill.ps1`（**単一プロセス**運転。重複起動禁止）
- 仕様:
  - 各chunk前に `.secrets\jq.env` 再読込（JQ_EMAIL/PASSWORD）
  - 429/401は指数バックオフ＋Retry-After、**連続no_token 2回でクールダウン30→…→300s**
  - `.secrets\jq_token.json` を自動維持（refresh循環）

## しきい値トリガ（自動再学習）
- ベースライン:
  - `.secrets\fin_parquet_baseline.txt`（parquet件数）
  - `.secrets\fin_norm_baseline.json`（as-of財務 rows/tickers）
- トリガ条件 いずれか成立で **T6→T7** 自動実行:
  - A) parquet +20
  - B) 直近15分更新 ≥10
  - C) fin_load_asof rows +500 以上 or tickers +10 以上
- 実行列:
  1. `scripts\fin_load_asof.py`
  2. `scripts\fin_features_v1.py --config configs\tdnet_2014.yaml`
  3. `scripts\t5_cv_setup.py --mode q4_test --train-start 2012-01-01 --liquidity loose`
  4. `scripts\model_lightgbm_v2.py --use-features`（派生比率・ログ・価格・イベント集約＋小規模グリッド）
  5. `scripts\calibrate_isotonic_v2.py --ppv-target 0.8`

## 監視コマンド（抜粋）
```powershell
Get-Content .\reports\jquants_fin_backfill.log -Tail 20
(gci .\data\raw\jquants\fin -Filter *.parquet | measure).Count
.\.venv\Scripts\python.exe scripts\fin_load_asof.py | Out-Null
Get-Content .\reports\fin_load_asof.log -Tail 1
Get-Content .\reports\model_lightgbm_v2.log -Tail 20
type .\reports\checks\tdnet_model_y_2x.json
type .\reports\checks\tdnet_model_y_2x_calib.json
KPIの読み方
tdnet_model_y_2x.json.oof.auc_roc >= 0.60 を暫定合格ライン

tdnet_model_y_2x_calib.json.thr_ppv80 != "none" を校正の合格ライン
