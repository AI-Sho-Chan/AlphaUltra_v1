Param(
  [ValidateSet('edinet','news','all')][string]$target='all'
)
Set-Location (Split-Path $MyInvocation.MyCommand.Path -Parent) | Out-Null
Set-Location ..
$ErrorActionPreference = "Stop"
$PY = ".\.venv\Scripts\python.exe"
$env:PYTHONPATH = (Get-Location).Path

.\.venv\Scripts\pip.exe install -q -r requirements_day4-5.txt

if ($target -in @('edinet','all')) {
  Write-Host "=== EDINET ingest ==="
  & $PY -m scripts.edinet_ingest --config configs\edinet.yaml
  & $PY -m scripts.edinet_validate --config configs\edinet.yaml
}

if ($target -in @('news','all')) {
  Write-Host "=== NEWS ingest ==="
  & $PY -m scripts.news_ingest_headlines --config configs\news.yaml
  & $PY -m scripts.news_validate --config configs\news.yaml
}

Write-Host "Done. See reports\checks"



