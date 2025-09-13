# --- AlphaUltra Day1-2 runner (py311 enforced) ---
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true

# Ensure dirs
New-Item -ItemType Directory -Force "data\raw","data\proc","reports\checks" | Out-Null

# Ensure venv (py311) and deps
if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
  & "scripts\env_use_py311.ps1"
}

$PY  = ".\.venv\Scripts\python.exe"
$PIP = ".\.venv\Scripts\pip.exe"

# Log
$log = "reports\checks\run_day1_2.log"
Start-Transcript -Path $log -Force

try {
  & $PY -m pip install --upgrade pip wheel setuptools
  & $PIP install -r requirements.txt

  Write-Host "=== Ingest ==="
  & $PY scripts\ingest_prices_yf.py --config "configs\base.yaml"

  Write-Host "=== Adjust ==="
  & $PY scripts\compute_adjusted.py --config "configs\base.yaml"

  Write-Host "=== Relative ==="
  & $PY scripts\compute_relative.py --config "configs\base.yaml"

  Write-Host "Done. See data\proc\ and reports\checks\."
}
finally {
  Stop-Transcript | Out-Null
}




