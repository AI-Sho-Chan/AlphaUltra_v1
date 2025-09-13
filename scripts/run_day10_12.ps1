Param([string]$task="y_2x")
Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
Set-Location (Split-Path $MyInvocation.MyCommand.Path -Parent) | Out-Null
Set-Location ..
New-Item -ItemType Directory -Force data\proc\model, reports\checks | Out-Null
.\.venv\Scripts\pip.exe install -q -r requirements_day10-12.txt
$env:PYTHONPATH=(Get-Location).Path
$PY=".\.venv\Scripts\python.exe"
& $PY -W ignore -m scripts.features_join   --config configs\model.yaml 1> reports\checks\features_join_run.log 2>&1
& $PY -W ignore -W ignore -m scripts.model_lightgbm --config configs\model.yaml --task $task 1> ("reports\checks\model_lgbm_run_"+$task+".log") 2>&1
Write-Host "Done. See reports\checks and data\proc\model"


