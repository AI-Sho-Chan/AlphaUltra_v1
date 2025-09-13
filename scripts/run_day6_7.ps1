Param(
  [ValidateSet('news','filings','edinet','all')][string]$target='all'
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Set-Location (Split-Path $MyInvocation.MyCommand.Path -Parent) | Out-Null
Set-Location ..

# ensure dirs
New-Item -ItemType Directory -Force data\proc\features_text, reports\checks | Out-Null

# deps
.\.venv\Scripts\pip.exe install -q -r requirements_day6-7.txt

# PYTHONPATH
$env:PYTHONPATH = (Get-Location).Path
$PY=".\.venv\Scripts\python.exe"

if ($target -in @('news','all')) {
  Write-Host "=== NEWS features ==="
  & $PY -m scripts.news_features_basic --config configs\text.yaml
}
if ($target -in @('filings','all')) {
  Write-Host "=== FILING features ==="
  & $PY -m scripts.filing_features_basic --config configs\text.yaml
}
if ($target -in @('edinet','all')) {
  Write-Host "=== EDINET features ==="
  & $PY -m scripts.edinet_features_basic --config configs\text.yaml
}

Write-Host "Done. See data\proc\features_text and reports\checks"



