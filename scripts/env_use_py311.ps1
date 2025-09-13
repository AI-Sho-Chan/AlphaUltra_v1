# Create .venv using Python 3.11 explicitly
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true

function Find-Py311 {
  if (Get-Command py -ErrorAction SilentlyContinue) {
    $out = (py -0p) -split "`n" | Where-Object { $_ -match "3\.11" } | Select-Object -First 1
    if ($out) { return "py -3.11" }
  }
  if (Get-Command python3.11 -ErrorAction SilentlyContinue) { return "python3.11" }
  if (Get-Command "C:\Python311\python.exe" -ErrorAction SilentlyContinue) { return "C:\Python311\python.exe" }
  throw "Python 3.11 縺瑚ｦ九▽縺九ｊ縺ｾ縺帙ｓ縲・https://www.python.org/downloads/release/python-311/ 縺九ｉ x64 繧貞ｰ主・縺励※縺上□縺輔＞縲・
}

$exe = Find-Py311
if (Test-Path ".\.venv") { Remove-Item -Recurse -Force ".\.venv" }
& $exe -m venv .venv

$PY  = ".\.venv\Scripts\python.exe"
$PIP = ".\.venv\Scripts\pip.exe"
& $PY -m pip install --upgrade pip wheel setuptools



