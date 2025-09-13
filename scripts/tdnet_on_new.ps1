param([string]$Config,[string]$Changed)
$ErrorActionPreference='Stop'
if(-not $Config){$Config='configs\tdnet.yaml'}; if(-not $Changed){$Changed=''}
$env:PYTHONPATH=(Get-Location).Path; $PY='.\\.venv\\Scripts\\python.exe'
$log='reports\\checks\\tdnet_rt.log'; New-Item -ItemType Directory -Force reports\\checks | Out-Null
$use = (Test-Path $Changed) ? "--input `"$Changed`"" : ""
cmd /c "$PY scripts\\tdnet_ingest.py --config $Config $use" *>> $log
cmd /c "$PY scripts\\tdnet_features.py --config $Config" *>> $log
("{0}`t{1}" -f 'data\\proc\\features_tdnet\\tdnet_event_features.parquet',(Test-Path 'data\\proc\\features_tdnet\\tdnet_event_features.parquet')) |
  Tee-Object -FilePath $log -Append | Out-String | Write-Host
