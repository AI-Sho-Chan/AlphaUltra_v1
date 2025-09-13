# Wave-0 end-to-end runner for TDNET-first ETL (PowerShell)
#
# Steps per the init prompt:
# - Crawl Kabutan disclosures (year loop)
# - CSV -> JSON bulk
# - TDNET features (start/end from configs/tdnet.yaml)
# - JP prices fetch (Stooq first -> YF fallback)
# - Build standard prices parquet
# - Align to next trading day and join
# - Healthcheck JSON
#
# Logs in reports/checks. Echo existence checks and tail -n 20.

Param(
  [string]$Start="2013-09-01",
  [string]$End=(Get-Date).ToString('yyyy-MM-dd')
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

New-Item -ItemType Directory -Force data\raw\kabutan, data\raw\tdnet, data\raw\prices, data\proc, data\proc\dataset, data\proc\features_tdnet, data\proc\prices, reports\checks | Out-Null

$PY = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $PY)) { $PY = "python" }

$logs = @{}
$logs.kabu = "reports/checks/kabu_crawl.log"
$logs.csv2json = "reports/checks/csv2json.log"
$logs.feat = "reports/checks/tdnet_features.log"
$logs.prices = "reports/checks/prices_jp_fetch_bulk.log"
$logs.align = "reports/checks/tdnet_align_next_trading.log"
$logs.health = "reports/checks/healthcheck_tdnet_fast_v2.log"

# Crawl by year
try {
  $d0=[DateTime]::Parse($Start); $d1=[DateTime]::Parse($End)
  for ($y=$d0.Year; $y -le $d1.Year; $y++) {
    $ys = [DateTime]::new($y,1,1)
    $ye = [DateTime]::new($y,12,31)
    if ($ys -lt $d0) { $ys = $d0 }
    if ($ye -gt $d1) { $ye = $d1 }
    $cmd = "$PY tools\\kabu_crawl_bs.py --start $($ys.ToString('yyyy-MM-dd')) --end $($ye.ToString('yyyy-MM-dd')) --sleep 0.3 --max-pages 0"
    cmd /c $cmd 1>> $logs.kabu 2>&1
  }
} catch { Write-Host "crawl failed: $_" }

# CSV -> JSON
try { cmd /c "$PY scripts\\csv2json_bulk.py" 1> $logs.csv2json 2>&1 } catch { }

# TDNET features
try { cmd /c "$PY scripts\\tdnet_features.py --config configs\\tdnet.yaml" 1> $logs.feat 2>&1 } catch { }

# Prices (includes standard build)
try { cmd /c "$PY scripts\\prices_jp_fetch_bulk.py" 1> $logs.prices 2>&1 } catch { }

# Align to next trading day & join
try { cmd /c "$PY scripts\\tdnet_align_join_next_trading.py" 1> $logs.align 2>&1 } catch { }

# Healthcheck
try { cmd /c "$PY scripts\\healthcheck_tdnet_fast_v2.py" 1> $logs.health 2>&1 } catch { }

# Reporting
Write-Host "--- REPORT: commit sha ---"
try { git rev-parse --short HEAD } catch { "no-git" }

Write-Host "--- REPORT: existence checks ---"
$jsonCount = (Get-ChildItem -Recurse -Filter *.json data\raw\tdnet 2>$null | Measure-Object).Count
Write-Host ("raw_tdnet_json_count: " + $jsonCount)
Write-Host ("features_exists: " + (Test-Path "data\proc\features_tdnet\tdnet_event_features.parquet"))
Write-Host ("panel_exists: " + (Test-Path "data\proc\dataset\tdnet_panel.parquet"))

Write-Host "--- REPORT: tail logs (last 20 lines each) ---"
foreach ($k in $logs.Keys) {
  Write-Host ("# " + $k + " -> " + $logs[$k])
  if (Test-Path $logs[$k]) { Get-Content $logs[$k] -Tail 20 }
}

Write-Host "Done Wave-0."

