# Quick Yahoo endpoint test
try {
  $r = Invoke-WebRequest -UseBasicParsing "https://query1.finance.yahoo.com/v8/finance/chart/AAPL?range=1mo&interval=1d"
  Write-Host "Yahoo HTTP status:" $r.StatusCode
  $len = ($r.Content | Out-String).Length
  Write-Host "Content length:" $len
} catch {
  Write-Warning $_
}



