# AlphaUltra Day1–2 Package

## What this delivers
- Ingest daily OHLCV + actions via yfinance
- Build adjusted close (vendor or manual fallback)
- Compute S&P500-relative forward returns for h={21,63,252}
- Outputs:
  - `data/proc/adj_prices/*.parquet`
  - `data/proc/labels/relative_returns.parquet`
  - `reports/checks/relative_returns_summary.csv`

## How to run (Windows PowerShell)
```powershell
Set-Location C:\AI\AlphaUltra_v1
# unzip contents here so paths match
.\scriptsun_day1_2.ps1
```

## Config
Edit `configs/base.yaml` to change universe or dates.

## Notes
- JP tickers are aligned to XNYS sessions by forward-filling non-trading days for relative-return computation.
- Actions are applied when vendor Adj Close is missing.
