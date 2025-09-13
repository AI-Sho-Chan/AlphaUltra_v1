Param([string]$tag=$(Get-Date -Format yyyyMMdd_HHmmss))
Set-StrictMode -Version Latest; $ErrorActionPreference="Stop"
$root=(Get-Location).Path; $checks="$root\reports\checks"; $share="$root\reports\share"
New-Item -ItemType Directory -Force $checks,$share | Out-Null

# 進行中のTranscriptを静かに終了（無ければ無視）
try { Stop-Transcript | Out-Null } catch {}

# 環境スナップショット
$envFile="$checks\env_$tag.txt"
$sec = if($env:SEC_USER_AGENT){"********"} else {"<empty>"}; $edn = if($env:EDINET_API_KEY){"********"} else {"<empty>"}
$pyV = if(Test-Path .\.venv\Scripts\python.exe){ & .\.venv\Scripts\python.exe -V } else {"<none>"}
$pipV= if(Test-Path .\.venv\Scripts\pip.exe){    & .\.venv\Scripts\pip.exe -V    } else {"<none>"}
$pl  = if(Test-Path .\.venv\Scripts\pip.exe){ (& .\.venv\Scripts\pip.exe list) -join "`r`n" } else {"<none>"}
@"
root=$root
date=$(Get-Date -Format s)
git_origin=$(git remote get-url origin 2>$null)
python=$pyV
pip=$pipV
SEC_USER_AGENT=$sec
EDINET_API_KEY=$edn

### pip list
$pl
"@ | Set-Content -Encoding UTF8 $envFile

# 収集対象
$globs=@(
  "$checks\*.log","$checks\*summary*.csv","$checks\*status*.txt",
  "configs\*.yaml","scripts\*.py","scripts\*.ps1","utils\*.py",
  "data\raw\prices\*.parquet","data\proc\adj_prices\*.parquet",
  "data\proc\labels\*.parquet","data\proc\features_text\*.parquet"
)
$files=@(); foreach($g in $globs){ $it=Get-ChildItem -Path $g -ErrorAction SilentlyContinue; if($it){ $files+=$it } }
$files = $files | Select-Object -Expand FullName -Unique
$paths=@($envFile); if($files){ $paths += $files }

# ロック回避（読み取り可能なものだけ残す）
$locked=@()
$paths2=@()
foreach($p in $paths){
  try { $s=[System.IO.File]::Open($p,'Open','Read','Read'); $s.Close(); $paths2+=$p }
  catch { $locked+=$p }
}
if($locked){ $locked | Set-Content -Encoding UTF8 "$checks\locked_$tag.txt"; $paths2 += "$checks\locked_$tag.txt" }

# 圧縮→URL表示
$zip="reports\share\debug_$tag.zip"
Compress-Archive -LiteralPath $paths2 -DestinationPath $zip -Force
Write-Host "ZIP -> $zip"
try{
  git add $zip,$envFile "$checks\locked_$tag.txt" 2>$null | Out-Null
  git commit -m "chore(debug): logs pack $tag" | Out-Null
  git push | Out-Null
  $sha=(git rev-parse HEAD).Trim()
  $remote=(git remote get-url origin)
  if($remote -match 'github\.com[:/](.+?)/(.+?)(\.git)?$'){ $owner=$Matches[1]; $name=$Matches[2] }
  $zipRel = ($zip.Substring($root.Length+1)) -replace '\\','/'
  Write-Host ("COMMIT: https://github.com/{0}/{1}/commit/{2}" -f $owner,$name,$sha)
  Write-Host ("ZIP:    https://github.com/{0}/{1}/blob/{2}/{3}" -f $owner,$name,$sha,$zipRel)
}catch{ Write-Warning "git push skipped. Share local ZIP: $zip" }




