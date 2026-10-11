param(
  [ValidateSet("setup", "validate", "train", "publish")]
  [string]$Action = "validate",
  [switch]$Activate,
  [string]$ComfyUIRoot = "$env:USERPROFILE\Downloads\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable\ComfyUI"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

if ($Action -eq "setup") {
  & powershell -ExecutionPolicy Bypass -File (Join-Path $RepoRoot "setup_rendering_learning.ps1") -ComfyUIRoot $ComfyUIRoot
  exit $LASTEXITCODE
}

$LocalConfig = Join-Path $RepoRoot "learning\rendering\train_config.local.json"
$ExampleConfig = Join-Path $RepoRoot "learning\rendering\train_config.example.json"

if (-not (Test-Path $LocalConfig)) {
  Copy-Item $ExampleConfig $LocalConfig
  Write-Host "[SETUP] Created learning\rendering\train_config.local.json"
  Write-Host "[SETUP] Run: powershell -ExecutionPolicy Bypass -File .\train_rendering.ps1 -Action setup"
  exit 2
}

$Args = @("src\rendering_learning.py", $Action, "--config", "learning\rendering\train_config.local.json")
if ($Action -eq "publish" -and $Activate) {
  $Args += "--activate"
}

python @Args
