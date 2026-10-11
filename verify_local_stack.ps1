param()

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

$Python = Join-Path $RepoRoot "tools\python312\python.exe"
if (-not (Test-Path $Python)) {
  $Python = "python"
}

Write-Host "[VERIFY] Ensuring Oracle is running..."
& powershell.exe -ExecutionPolicy Bypass -File (Join-Path $RepoRoot "oracle_local.ps1") -Action start
if ($LASTEXITCODE -ne 0) {
  throw "Oracle start failed"
}

Write-Host "[VERIFY] Ensuring project-local Ollama is running..."
& powershell.exe -ExecutionPolicy Bypass -File (Join-Path $RepoRoot "local_ai.ps1") -Action start
if ($LASTEXITCODE -ne 0) {
  throw "Local AI start failed"
}

Write-Host "[VERIFY] Running disposable Oracle/Git/local-AI integration test..."
& $Python (Join-Path $RepoRoot "src\local_stack_integration_test.py")
if ($LASTEXITCODE -ne 0) {
  throw "Local stack integration test failed"
}

Write-Host "[VERIFY:LOCAL-STACK:OK]"
