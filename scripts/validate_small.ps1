#requires -Version 5
param(
  [string]$StartA="2013-11-10",
  [string]$EndA  ="2013-11-20",
  [string]$StartB="2025-06-01",
  [string]$EndB  ="2025-08-31"
)

$ErrorActionPreference = "Continue"
$PY = ".\.venv\Scripts\python.exe"

Write-Host ("Python " + (& $PY -V))

if (-not $env:KABUTAN_COOKIE -or $env:KABUTAN_COOKIE.Length -lt 20) {
  Write-Host "KABUTAN_COOKIE EMPTY. STOP."
  exit 1
}

function Run-Crawl([string]$s,[string]$e,[string]$tag){
  New-Item -ItemType Directory -Force -Path reports\checks | Out-Null
  try {
    & $PY tools\kabu_crawl_bs.py --start $s --end $e --sleep 0.25 --max-pages 0 *>&1 |
      Tee-Object "reports\checks\kabu_crawl_$tag.log"
  } catch {
    Write-Host "[crawl-$tag] caught: $($_.Exception.Message)"
  }
}

function Get-P90Rows([datetime]$s,[datetime]$e){
  $vals = @()
  for ($d=$s; $d -le $e; $d=$d.AddDays(1)) {
    $ymd = $d.ToString('yyyy-MM-dd')
    $csv = "data/raw/kabutan/$ymd/tdnet.csv"
    if (Test-Path $csv) {
      $n = (Get-Content $csv -Encoding UTF8 | Measure-Object -Line).Lines
      $vals += [int]([Math]::Max(0,$n-1))
    } else {
      $vals += 0
    }
  }
  if (-not $vals.Count) { return 0 }
  $srt = $vals | Sort-Object
  $idx = [Math]::Max([int][Math]::Ceiling(0.9 * $srt.Count) - 1, 0)
  return [int]$srt[$idx]
}

# ---- Crawl A/B ----
Run-Crawl $StartA $EndA "A"
Run-Crawl $StartB $EndB "B"

$p90A = Get-P90Rows $StartA $EndA
$p90B = Get-P90Rows $StartB $EndB
Write-Host ("p90A=" + $p90A)
Write-Host ("p90B=" + $p90B)

# ---- Range A pipeline ----
if (Test-Path .\configs\tdnet.yaml) {
  (Get-Content .\configs\tdnet.yaml) `
    -replace 'start_date:.*',("start_date: {0}" -f $StartA) `
    -replace 'end_date:.*',  ("end_date:   {0}" -f $EndA) |
    Set-Content -Encoding UTF8 .\configs\tdnet_A.yaml
} else {
  @"
paths:
  tdnet_raw: data/raw/tdnet
  tdnet_features: data/proc/features_tdnet/tdnet_event_features.parquet
params:
  start_date: $StartA
  end_date:   $EndA
"@ | Set-Content -Encoding UTF8 .\configs\tdnet_A.yaml
}

try { & $PY scripts\csv2json_bulk.py                         *>&1 | Tee-Object reports\checks\csv2json.log } catch {}
try { & $PY scripts\tdnet_features.py --config configs\tdnet_A.yaml *>&1 | Tee-Object reports\checks\tdnet_features.log } catch {}
try { & $PY scripts\prices_jp_fetch_bulk.py                 *>&1 | Tee-Object reports\checks\prices_jp_fetch_bulk.log } catch {}
try { & $PY scripts\price_std_build.py                      *>&1 | Tee-Object reports\checks\price_std_build.log } catch {}
try { & $PY scripts\tdnet_align_join_next_trading.py        *>&1 | Tee-Object reports\checks\tdnet_align_next_trading.log } catch {}
try { & $PY scripts\healthcheck_tdnet_fast_v2.py            *>&1 | Tee-Object reports\checks\healthcheck_tdnet_fast_v2.log } catch {}

# ---- Report ----
if (Get-Command git -ErrorAction SilentlyContinue) { git rev-parse HEAD }
foreach ($f in @(
  "reports\checks\kabu_crawl_A.log",
  "reports\checks\csv2json.log",
  "reports\checks\tdnet_features.log",
  "reports\checks\prices_jp_fetch_bulk.log",
  "reports\checks\tdnet_align_next_trading.log",
  "reports\checks\healthcheck_tdnet_fast_v2.log"
)) {
  if (Test-Path $f) { Write-Host "`n--- tail $f ---"; Get-Content $f -Tail 20 }
}

(Get-ChildItem -Recurse -Filter *.json data\raw\tdnet | Measure-Object).Count
Test-Path data\proc\features_tdnet\tdnet_event_features.parquet
Test-Path data\proc\dataset\tdnet_panel.parquet
