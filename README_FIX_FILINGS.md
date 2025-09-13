# Fix: EDGAR filings layout + summary

**Problem**: Some filings were saved under wrong nested paths like:
```
data/raw/filings/us/0000789019/0000320193/0000320193-25-000071/metadata.json
```
Correct layout must be:
```
data/raw/filings/us/<CIK>/<accessionNumber>/metadata.json
```

## Apply

PowerShell:
```powershell
Set-Location C:\AI\AlphaUltra_v1
$PY=".\.venv\Scripts\python.exe"
$env:PYTHONPATH=(Get-Location).Path

# 1) repair layout
& $PY -m scripts.repair_filings_layout

# 2) regenerate summary
& $PY -m scripts.make_filings_summary

# 3) verify
Get-Content .\reports\checks\filings_summary.csv -TotalCount 20
dir .\data\raw\filings\us\0000320193 -Depth 2
dir .\data\raw\filings\us\0000789019 -Depth 2
```
