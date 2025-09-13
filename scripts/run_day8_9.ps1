Param([string]$config="configs\labels.yaml")
Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
Set-Location (Split-Path $MyInvocation.MyCommand.Path -Parent) | Out-Null
Set-Location ..
$env:PYTHONPATH=(Get-Location).Path
$PY=".\.venv\Scripts\python.exe"
New-Item -ItemType Directory -Force data\proc\labels, reports\checks | Out-Null
.\.venv\Scripts\pip.exe install -q -r requirements_day8-9.txt
Write-Host "=== LABELS ==="
& $PY -m scripts.label_make --config $config
Write-Host "Done. See data\proc\labels\targets.parquet and reports\checks\labels_summary.csv"

