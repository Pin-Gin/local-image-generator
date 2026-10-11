$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

Write-Host "[BUILD] Installing desktop dependencies..."
python -m pip install -r requirements-desktop.txt

Write-Host "[BUILD] Building MEMORIELA.exe..."
python -m PyInstaller `
  --noconfirm `
  --clean `
  --windowed `
  --name MEMORIELA `
  --add-data "ui;ui" `
  --add-data "config;config" `
  --add-data "profiles;profiles" `
  --add-data "intent;intent" `
  --add-data "schemas;schemas" `
  --add-data "workflows;workflows" `
  --hidden-import webview.platforms.edgechromium `
  src\desktop_app.py

Write-Host "[BUILD:OK] dist\MEMORIELA\MEMORIELA.exe"
