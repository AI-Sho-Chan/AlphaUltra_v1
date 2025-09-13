# RUNBOOK（運用手順）

## 夜間バッチ（四半期財務バックフィル）
- 単一プロセスのみ稼働：scripts\run_fin_backfill.ps1
- 認証：
  - .secrets\jq.env（JQ_EMAIL/JQ_PASSWORD）
  - .secrets\jq_token.json はスクリプトが自動作成/更新
- レート制限対策：
  - no_token 連続検知→指数クールダウン（30→60→…最大300s）
  - 各chunk間 3–7s ジッター

## しきい値トリガ（自動再学習）
成立で自動実行：A) parquet +20 / B) 15分で更新≥10 / C) fin_rows +500 or tickers +10  
実行列：
1) fin_load_asof.py
2) fin_features_v1.py（2014設定）
3) t5_cv_setup.py（--mode q4_test --train-start 2012-01-01 --liquidity loose）
4) model_lightgbm_v2.py（--use-features：派生比率・ログ・価格・イベント集約＋グリッド）
5) calibrate_isotonic_v2.py（ppv_target=0.8）

## 日中の監視コマンド（抜粋）
- tail 取得ログ：Get-Content reports\jquants_fin_backfill.log -Tail 50
- parquet件数： (gci data\raw\jquants\fin -Filter *.parquet | measure).Count
- 正規化財務： .\.venv\Scripts\python.exe scripts\fin_load_asof.py ; Get-Content reports\fin_load_asof.log -Tail 1
- 学習ログ：Get-Content reports\model_lightgbm_v2.log -Tail 50
- 校正ログ：Get-Content reports\calibrate_isotonic_v2.log -Tail 50
