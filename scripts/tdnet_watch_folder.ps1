param(
  [string]$Inbox,
  [string]$Config
)
$ErrorActionPreference = 'Stop'
if (-not $Inbox)  { $Inbox  = 'data\raw\tdnet\inbox' }
if (-not $Config) { $Config = 'configs\tdnet.yaml' }

New-Item -ItemType Directory -Force $Inbox,'reports\checks' | Out-Null
$log = 'reports\checks\tdnet_watch.log'
"=== TDNET watcher start: $(Get-Date -Format o)" | Set-Content -Encoding UTF8 $log
$env:PYTHONPATH = (Get-Location).Path

$action = {
  param($source,$eventArgs)
  Start-Sleep -Milliseconds 500
  $changed = $eventArgs.FullPath
  Add-Content -Path 'reports\checks\tdnet_watch.log' -Value ("NEW: " + $changed)
  & .\scripts\tdnet_on_new.ps1 -Config $using:Config -Changed $changed
}

$fsw  = New-Object System.IO.FileSystemWatcher (Resolve-Path $Inbox), '*.csv',  $true
$fsw2 = New-Object System.IO.FileSystemWatcher (Resolve-Path $Inbox), '*.tsv',  $true
$fsw3 = New-Object System.IO.FileSystemWatcher (Resolve-Path $Inbox), '*.json', $true
$fsw.EnableRaisingEvents=$true; $fsw2.EnableRaisingEvents=$true; $fsw3.EnableRaisingEvents=$true
Register-ObjectEvent $fsw  Created -Action $action | Out-Null
Register-ObjectEvent $fsw2 Created -Action $action | Out-Null
Register-ObjectEvent $fsw3 Created -Action $action | Out-Null

Write-Host "Watching $Inbox. Ctrl+C to stop."
while ($true) { Start-Sleep 2 }
