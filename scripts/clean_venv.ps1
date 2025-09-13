if (Test-Path ".\.venv") { Remove-Item -Recurse -Force ".\.venv"; Write-Host "Removed .venv" } else { Write-Host ".venv not found" }




