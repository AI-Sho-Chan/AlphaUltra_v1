\
param(
  [string]$ProjectRoot = "C:\AI\AlphaUltra_v1"
)
$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$ProjectRoot\scripts\tdnet_watch_folder.ps1`""
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -Compatibility Win8
Register-ScheduledTask -TaskName "AlphaUltra_TDNET_Watcher" -Action $Action -Trigger $Trigger -Settings $Settings -Description "Watch TDNET inbox and process files" -Force
Write-Host "Registered task 'AlphaUltra_TDNET_Watcher'."
