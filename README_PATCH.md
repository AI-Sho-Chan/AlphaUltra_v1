# Patch: enforce Python 3.11 on Windows

**Root cause**: Your venv used Python 3.13. `pandas==2.2.2` has no Windows wheels for 3.13 and tries to build from source, which fails.  
**Fix**: Use Python **3.11** for this project.

## How to apply
1) Download this patch zip and extract to your repo root (`C:\AI\AlphaUltra_v1`), overwrite files.
2) Run:
```powershell
Set-Location C:\AI\AlphaUltra_v1
.\scripts\clean_venv.ps1
.\scriptsun_day1_2.ps1
```
This will create a `.venv` with **Python 3.11**, install deps, and run the Day1–2 pipeline with logging to `reports\checks\run_day1_2.log`.

If you do not have Python 3.11 installed, install it from: https://www.python.org/downloads/release/python-311/
