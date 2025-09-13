# Day10-12: LightGBM Baseline with Purged CV

## Run
```powershell
Set-Location C:\AI\AlphaUltra_v1
Expand-Archive "$env:USERPROFILE\Downloads\AlphaUltra_Day10-12_pack.zip" -DestinationPath . -Force
$env:PYTHONPATH=(Get-Location).Path; .\scripts\run_day10_12.ps1 -task y_2x
```
Tasks: `y_2x`, `hit_rel_1M_10p`, `hit_rel_3M_20p`, `hit_rel_12M_50p`

## Outputs
- `reports/checks/features_join_run.log`
- `reports/checks/model_cv_metrics_<task>.csv`
- `reports/checks/model_cv_summary_<task>.json`
- `reports/checks/feature_importance_<task>.csv` (if available)
- `data/proc/model/oof_<task>.parquet`
