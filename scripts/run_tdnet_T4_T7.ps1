param([string]$Config="configs\tdnet_model.yaml")
$ErrorActionPreference="Stop"
$env:PYTHONPATH=(Get-Location).Path
$PY=".\\.venv\\Scripts\\python.exe"
$log="reports\\checks\\tdnet_T4_T7.log"
New-Item -ItemType Directory -Force reports\\checks | Out-Null
cmd /c "$PY -u scripts\\tdnet_expand_prices.py --config $Config" 2>&1 | Tee-Object -FilePath $log
cmd /c "$PY -u scripts\\tdnet_align_join.py  --config $Config" 2>&1 | Tee-Object -FilePath $log -Append
cmd /c "$PY -u scripts\\labels_make.py      --config $Config" 2>&1 | Tee-Object -FilePath $log -Append
"{0}`t{1}" -f "dataset", (Test-Path "data\\proc\\dataset\\tdnet_panel.parquet") | Tee-Object -FilePath $log -Append
"{0}`t{1}" -f "labels",  (Test-Path "data\\proc\\labels\\targets.parquet")      | Tee-Object -FilePath $log -Append
