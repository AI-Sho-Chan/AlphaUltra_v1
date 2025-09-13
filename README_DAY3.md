# Day3: Filings Ingestion Pack

目的:
- EDGAR(US)の 10-K/10-Q/8-K を **acceptanceDatetime** ベースで取得し、リーケージ耐性の原データを保存。
- EDINET/TDnet は **stub** 同梱。後段で実装・切替可能。

前提:
- 既存リポ構成: C:\AI\AlphaUltra_v1
- .venv は Python 3.11
- SEC User-Agent を環境変数に設定: `setx SEC_USER_AGENT "youremail@example.com AlphaUltra/1.0"`

展開先:
- リポ直下に展開。既存ファイルは上書きされない。

実行(例):
```powershell
Set-Location C:\AI\AlphaUltra_v1
$env:PYTHONPATH = (Get-Location).Path
$PY = ".\.venv\Scripts\python.exe"

# 依存導入（requests, python-dateutilは既存requirementsで充足）
$PY -m pip install --disable-pip-version-check --no-input tenacity==9.0.0

# US: 直近7日, シリーズは 10-K/10-Q/8-K
& $PY -m scripts.edgar_ingest --config configs\filings.yaml --days 7 --forms 10-K 10-Q 8-K

# サマリ確認
& $PY -m scripts.validate_filings --config configs\filings.yaml
Get-Content .\reports\checks\filings_summary.csv -TotalCount 50
```

出力:
- data/raw/filings/us/{cik}/{accession}/metadata.json
- data/raw/filings/us/{cik}/{accession}/primary_doc.(xml|htm|txt) など
- reports/checks/filings_summary.csv

設定:
- configs/filings.yaml でCIKと対象フォーム、User-Agentを管理。
