# HANDOVER（引き継ぎ）

## 何をすれば動くか（最短）
1. ルート: C:\AI\AlphaUltra_v1
2. 認証：.secrets\jq.env（JQ_EMAIL/JQ_PASSWORD）をUTF-8 or ASCIIで配置
3. 夜間バッチ（単一プロセスのみ）:
   powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_fin_backfill.ps1
4. 監視：RUNBOOKのコマンド群
5. 成果確認：reports\checks\tdnet_model_y_2x*.json と AUCログ

## 注意
- 並列起動禁止（429誘発）
- しきい値達成時の自動再学習によりログが増える（コミット前に必要ファイルのみAdd）
