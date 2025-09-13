# Ingest Fix (Yahoo hardening + Stooq fallback)

**Why**: Yahoo endpoints may return no data due to region blocks or Cloudflare. This patch:
- sets a proper User-Agent for yfinance,
- falls back to **Stooq** via `pandas-datareader`,
- switches benchmark to **SPY**,
- uses `JPY=X` for FX.

## Apply
1) Extract zip to repo root (`C:\AI\AlphaUltra_v1`), overwrite files.
2) Install extra dependency:
```powershell
C:\AI\AlphaUltra_v1\.venv\Scripts\pip.exe install pandas-datareader==0.10.0
```
3) Run (PowerShell):
```powershell
Set-Location C:\AI\AlphaUltra_v1
$env:PYTHONPATH = (Get-Location).Path
$PY = ".\.venv\Scripts\python.exe"
& $PY -m scripts.ingest_prices_yf --config configsase.yaml
& $PY -m scripts.compute_adjusted --config configsase.yaml
& $PY -m scripts.compute_relative --config configsase.yaml
```
4) Check outputs:
- `data/raw/prices/*.parquet` present
- `data/proc/adj_prices/*.parquet` present
- `reports/checks/relative_returns_summary.csv` present

## Diagnose Yahoo
```powershell
.\scripts\diagnose_yahoo.ps1
```
If HTTP not 200, fallback will handle data via Stooq for equities/ETF.
