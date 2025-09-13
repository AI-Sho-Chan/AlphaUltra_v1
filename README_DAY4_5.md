# Day4-5 Pack (EDINET minimal + News headlines)

## Run
```powershell
Set-Location C:\AI\AlphaUltra_v1
Expand-Archive "$env:USERPROFILE\Downloads\AlphaUltra_Day4-5_pack.zip" -DestinationPath . -Force
$env:PYTHONPATH=(Get-Location).Path
.\scripts\run_day4_5.ps1              # both EDINET + NEWS
# or per target:
.\scripts\run_day4_5.ps1 -target edinet
.\scripts\run_day4_5.ps1 -target news
```

## Outputs
- `reports/checks/edinet_summary.csv`, `reports/checks/edinet_status.txt`
- `reports/checks/news_summary.csv`, `reports/checks/news_counts.csv`
- Raw: `data/raw/edinet/<YYYY-MM-DD>/<docID>/metadata.json`
- Raw: `data/raw/news/headlines.parquet`
