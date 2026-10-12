param(
  [switch]$Apply
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$OracleScript = Join-Path $RepoRoot "oracle_local.ps1"
$Python = Join-Path $RepoRoot "tools\python312\python.exe"
$JsonReset = Join-Path $RepoRoot "scripts\migration\reset_free_json_store.py"

if (-not $Apply) {
  Write-Host "[LOCAL-AI-RESET:DRY-RUN] no state changed; rerun with -Apply"
  Write-Host "[LOCAL-AI-RESET:ORACLE] recreate LOCALRAG_KB1 from scratch using oracle_local.ps1 -Action reset-schema"
  Write-Host "[LOCAL-AI-RESET:FILES] clear local JSON staging/accepted/receipts and bootstrap free.test.background_scene@1"
  Write-Host "[LOCAL-AI-RESET:PRESERVE] Oracle container/volume/tablespace, LR_SCHEMA_META recreation, models, SQLite, tools, reference images"
  exit 0
}

if (-not (Test-Path -LiteralPath $OracleScript -PathType Leaf)) {
  throw "oracle_local.ps1 not found: $OracleScript"
}
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
  throw "project Python not found: $Python"
}
if (-not (Test-Path -LiteralPath $JsonReset -PathType Leaf)) {
  throw "JSON reset script not found: $JsonReset"
}

Push-Location $RepoRoot
try {
  Write-Host "[LOCAL-AI-RESET:ORACLE:START]"
  & $OracleScript -Action reset-schema
  if ($LASTEXITCODE -ne 0) {
    throw "Oracle schema reset failed"
  }
  Write-Host "[LOCAL-AI-RESET:ORACLE:OK] LOCALRAG_KB1 recreated empty"

  Write-Host "[LOCAL-AI-RESET:JSON:START]"
  & $Python $JsonReset --apply
  if ($LASTEXITCODE -ne 0) {
    throw "FREE JSON store reset failed"
  }
  Write-Host "[LOCAL-AI-RESET:JSON:OK]"

  Write-Host "[LOCAL-AI-RESET:OK]"
  Write-Host "[LOCAL-AI-RESET:NOTE] Oracle is intentionally empty after reset; new local-AI accepted knowledge will repopulate it explicitly."
}
finally {
  Pop-Location
}
