$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

$LegacyDist = Join-Path $RepoRoot "dist\MEMORIELA"
if (Test-Path $LegacyDist) {
  Write-Host "[CLEAN] Removing legacy dist\MEMORIELA..."
  Remove-Item -Recurse -Force $LegacyDist
}

Write-Host "[BUILD] Installing desktop dependencies..."
python -m pip install -r requirements-desktop.txt

Write-Host "[BUILD] Building local-RAG.exe..."
python -m PyInstaller `
  --noconfirm `
  --clean `
  --windowed `
  --name local-RAG `
  --add-data "ui;ui" `
  --add-data "config;config" `
  --add-data "profiles;profiles" `
  --add-data "intent;intent" `
  --add-data "schemas;schemas" `
  --add-data "workflows;workflows" `
  --add-data "shared;shared" `
  --add-data "domains;domains" `
  --add-data "learning\registry;learning\registry" `
  --hidden-import webview.platforms.edgechromium `
  src\desktop_app.py

Write-Host "[BUILD:OK] dist\local-RAG\local-RAG.exe"
