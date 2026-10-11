param(
  [ValidateSet("setup", "prepare", "validate", "train", "publish")]
  [string]$Action = "validate",
  [switch]$Activate,
  [switch]$SkipDependencyInstall,
  [switch]$Sequential,
  [int]$StartId = 1,
  [switch]$Replace,
  [switch]$DryRun,
  [string]$ComfyUIRoot = "$env:USERPROFILE\Downloads\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable\ComfyUI"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

if ($Action -eq "setup") {
  $setupArgs = @(
    "-ExecutionPolicy", "Bypass",
    "-File", (Join-Path $RepoRoot "setup_rendering_learning.ps1"),
    "-ComfyUIRoot", $ComfyUIRoot
  )
  if ($SkipDependencyInstall) {
    $setupArgs += "-SkipDependencyInstall"
  }
  & powershell @setupArgs
  exit $LASTEXITCODE
}

if ($Action -eq "prepare") {
  $PreparePython = Join-Path $RepoRoot "tools\python312\python.exe"
  if (-not (Test-Path $PreparePython)) {
    $PreparePython = "python"
  }
  $prepareArgs = @(
    "src\rendering_dataset_prepare.py",
    "--manifest", "learning\rendering\generation_manifest.json",
    "--incoming", "learning\rendering\incoming",
    "--dataset", "learning\rendering\dataset\20_mdanime",
    "--start-id", $StartId
  )
  if ($Sequential) {
    $prepareArgs += "--sequential"
  }
  if ($Replace) {
    $prepareArgs += "--replace"
  }
  if ($DryRun) {
    $prepareArgs += "--dry-run"
  }
  & $PreparePython @prepareArgs
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
