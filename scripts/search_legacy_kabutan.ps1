\
param([string]$Old="C:\AI\AlphaUltra")
if(-not (Test-Path $Old)){ Write-Host "not found: $Old"; exit 1 }
Get-ChildItem -Path $Old -Recurse -File -Include *kabutan*,*tdnet*,*適時開示* |
  Select-Object FullName, Length, LastWriteTime |
  Sort-Object LastWriteTime -Descending
