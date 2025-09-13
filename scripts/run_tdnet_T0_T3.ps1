# T0–T3 runner: TDNET ingest -> features
param(
  [string]$Config = "configs\tdnet.yaml"
)
$ErrorActionPreference = "Stop"
$root = Get-Location
$PY = ".\.venv\Scripts\python.exe"
$env:PYTHONPATH = $root.Path

# ensure dirs
New-Item -ItemType Directory -Force data\raw\tdnet\inbox, data\proc\features_tdnet, reports\checks | Out-Null

# run
& $PY -m pip install python-dateutil pyyaml pandas pyarrow 1>$null 2>$null

$log = "reports\checks\tdnet_T0_T3.log"
"=== TDNET T0-T3 ===" | Set-Content -Encoding UTF8 $log
cmd /c "$PY scripts\tdnet_ingest.py --config $Config" *>> $log
cmd /c "$PY scripts\tdnet_features.py --config $Config" *>> $log

# checks
$ok = Test-Path "data\proc\features_tdnet\tdnet_event_features.parquet"
"{0}`t{1}" -f "data\proc\features_tdnet\tdnet_event_features.parquet", $ok | Tee-Object -FilePath $log -Append | Out-String | Write-Host
Write-Host "Log -> $log"
