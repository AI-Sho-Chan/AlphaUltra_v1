# Day8-9: Label generation (2x/10x/relative)

## Run
```powershell
Set-Location C:\AI\AlphaUltra_v1
Expand-Archive "$env:USERPROFILE\Downloads\AlphaUltra_Day8-9_pack.zip" -DestinationPath . -Force
$env:PYTHONPATH=(Get-Location).Path; .\scripts\run_day8_9.ps1
```

## Outputs
- `data/proc/labels/targets.parquet`
- `reports/checks/labels_summary.csv`
