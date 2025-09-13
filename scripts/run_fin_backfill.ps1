Param()
$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = Split-Path -Parent $scriptDir
Set-Location $repo

function Load-JQEnv {
  $envPath = Join-Path $repo '.secrets/jq.env'
  if (Test-Path $envPath) {
    Get-Content $envPath | ForEach-Object {
      if ($_ -match '^\s*#') { return }
      if ($_ -match '=') {
        $k,$v = $_.Split('=',2)
        $k = $k.Trim()
        # strip potential BOM
        $k = $k -replace "^\uFEFF",""
        if ($k -in @('JQ_EMAIL','JQ_PASSWORD')) { [Environment]::SetEnvironmentVariable($k, $v.Trim(), 'Process') }
      }
    }
  }
}
Load-JQEnv

$PY = Join-Path $repo '.\.venv\Scripts\python.exe'
if (-not (Test-Path $PY)) { $PY = 'python' }

$log = Join-Path $repo 'reports/jquants_fin_backfill.log'
if (-not (Test-Path (Split-Path $log))) { New-Item -ItemType Directory -Path (Split-Path $log) -Force | Out-Null }

# Configurable chunk size via env or default 100
$chunkSize = [int]([Environment]::GetEnvironmentVariable('JQ_FIN_CHUNK_SIZE','Process'))
if (-not $chunkSize -or $chunkSize -le 0) { $chunkSize = 100 }

# Compute window end: next 05:00 from now if current time >= 05:00, otherwise today 05:00
$now = Get-Date
if ($now.Hour -lt 5) {
  $endAt = $now.Date.AddHours(5)
} else {
  $endAt = $now.Date.AddDays(1).AddHours(5)
}

$iter = 0
$consecZero = 0
$lastFinCount = if (Test-Path 'data\raw\jquants\fin') { (Get-ChildItem 'data\raw\jquants\fin' -Filter '*.parquet' | Measure-Object).Count } else { 0 }

# Threshold baselines
$baselineParqPath = Join-Path $repo '.secrets/fin_parquet_baseline.txt'
$baselineNormPath = Join-Path $repo '.secrets/fin_norm_baseline.json'
if (-not (Test-Path $baselineParqPath)) { Set-Content -Path $baselineParqPath -Value $lastFinCount -Encoding UTF8 }
if (-not (Test-Path $baselineNormPath)) {
  try {
    $normOut = & $PY scripts/fin_load_asof.py
    $normObj = $normOut | ConvertFrom-Json
    Set-Content -Path $baselineNormPath -Value ($normObj | ConvertTo-Json -Compress) -Encoding UTF8
  } catch {
    Set-Content -Path $baselineNormPath -Value '{"rows":0,"tickers":0}' -Encoding UTF8
  }
}

function Get-BaselineParquet { try { [int](Get-Content $baselineParqPath -ErrorAction Stop) } catch { 0 } }
function Get-BaselineNorm { try { Get-Content $baselineNormPath -Raw | ConvertFrom-Json } catch { @{ rows = 0; tickers = 0 } } }

function Get-UpdatedIn15Min {
  if (-not (Test-Path 'data\raw\jquants\fin')) { return 0 }
  $cut = (Get-Date).AddMinutes(-15)
  return (Get-ChildItem 'data\raw\jquants\fin' -Filter '*.parquet' | Where-Object { $_.LastWriteTime -gt $cut } | Measure-Object).Count
}

# Cooldown management for no_token streaks (max 5 minutes)
$noTokenStreak = 0
$cooldownSec = 30
while ((Get-Date) -lt $endAt) {
  # reload creds each chunk as a safeguard
  Load-JQEnv
  $ts = (Get-Date).ToString('s')
  $args = @('scripts/jquants_bulk_financials.py','--chunk','next','--chunk-size',"$chunkSize")
  try {
    $out = & $PY @args
  } catch {
    $out = '{"error":"exec_failed"}'
  }
  "${ts}`t$out" | Out-File -FilePath $log -Append -Encoding UTF8
  $iter += 1
  # parse result JSON for fin_ok and fail_reasons
  try {
    $obj = $out | ConvertFrom-Json
    $ok  = [int]$obj.fin_ok
    if ($ok -eq 0) { $consecZero++ } else { $consecZero = 0 }
    if ($consecZero -ge 3 -and $chunkSize -gt 50) {
      $chunkSize = 50
      "${ts}`t{`"note`":`"downshift_chunk_to_50`"}" | Out-File -FilePath $log -Append -Encoding UTF8
    }
    # detect continuous no_token failures per chunk
    $noTok = 0
    try { if ($obj.fail_reasons -and $obj.fail_reasons.no_token) { $noTok = [int]$obj.fail_reasons.no_token } } catch {}
    $fail = try { [int]$obj.fin_fail } catch { 0 }
    # consider "full no_token chunk" when no_token covers all failures
    if ($fail -gt 0 -and $noTok -ge $fail) {
      $noTokenStreak += 1
    } else {
      $noTokenStreak = 0; $cooldownSec = 30
    }
    if ($noTokenStreak -ge 2) {
      # cooldown with exponential backoff up to 300s
      $cd = [Math]::Min(300, [int]$cooldownSec)
      "${ts}`t{`"note`":`"cooldown_no_token`",`"seconds`":$cd,`"streak`":$noTokenStreak}" | Out-File -FilePath $log -Append -Encoding UTF8
      Start-Sleep -Seconds $cd
      $cooldownSec = [Math]::Min(300, [int]($cooldownSec * 2))
    }
  } catch { }

  # current parquet stats
  $curFinCount = if (Test-Path 'data\raw\jquants\fin') { (Get-ChildItem 'data\raw\jquants\fin' -Filter '*.parquet' | Measure-Object).Count } else { 0 }
  $updated15 = Get-UpdatedIn15Min
  $baselineCount = Get-BaselineParquet
  $deltaFiles = $curFinCount - $baselineCount

  # read last normalized counts from logs if exists
  $lastNormObj = Get-BaselineNorm
  $normRun = $false
  $triggered = $false

  # Condition A or B triggers immediate norm recompute for Condition C check
  if ($deltaFiles -ge 20 -or $updated15 -ge 10) { $normRun = $true }

  if ($normRun) {
    try { $normOut = & $PY scripts/fin_load_asof.py; $normObj = $normOut | ConvertFrom-Json } catch { $normObj = $null }
  } else { $normObj = $null }

  # Evaluate thresholds
  if ($deltaFiles -ge 20) { $triggered = $true }
  if ($updated15 -ge 10)  { $triggered = $true }
  if ($normObj) {
    $dRows   = ([int]$normObj.rows)   - ([int]$lastNormObj.rows)
    $dTicks  = ([int]$normObj.tickers)- ([int]$lastNormObj.tickers)
    if ($dRows -ge 500 -or $dTicks -ge 10) { $triggered = $true }
  }

  if ($triggered) {
    try {
      if (-not $normObj) { $normOut = & $PY scripts/fin_load_asof.py; $normObj = $normOut | ConvertFrom-Json }
      & $PY scripts/fin_features_v1.py --config configs/tdnet_2014.yaml | Out-Null
      & $PY scripts/t5_cv_setup.py --config configs/tdnet_2014.yaml --label y_2x --purge 20 --embargo 5 --cluster 60 --mode q4_test --train-start 2012-01-01 --liquidity loose --out reports/cv_t5_y_2x_v2.json | Out-Null
      & $PY scripts/model_lightgbm_v2.py --config configs/tdnet_2014.yaml --label y_2x --folds-config reports/cv_t5_y_2x_v2.json --use-features | Out-Null
      & $PY scripts/calibrate_isotonic_v2.py --oof reports/checks/tdnet_model_y_2x_oof.parquet --ppv-target 0.8 | Out-Null
      # update baselines
      Set-Content -Path $baselineParqPath -Value $curFinCount -Encoding UTF8
      if ($normObj) { Set-Content -Path $baselineNormPath -Value ($normObj | ConvertTo-Json -Compress) -Encoding UTF8 }
      "${ts}`t{`"note`":`"threshold_triggered`",`"delta_files`":$deltaFiles,`"updated_15m`":$updated15}" | Out-File -FilePath $log -Append -Encoding UTF8
    } catch {
      "${ts}`t{`"error`":`"threshold_pipeline_failed`"}" | Out-File -FilePath $log -Append -Encoding UTF8
    }
  }

  $lastFinCount = $curFinCount

  # brief pause to be gentle between chunks
  if ((Get-Date) -lt $endAt) { Start-Sleep -Seconds (Get-Random -Minimum 3 -Maximum 8) }
}
