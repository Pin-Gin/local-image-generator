param(
  [ValidateSet("validate", "train", "publish")]
  [string]$Action = "validate",
  [switch]$Activate
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

$LocalConfig = Join-Path $RepoRoot "learning\rendering\train_config.local.json"
$ExampleConfig = Join-Path $RepoRoot "learning\rendering\train_config.example.json"

if (-not (Test-Path $LocalConfig)) {
  Copy-Item $ExampleConfig $LocalConfig
  Write-Host "[SETUP] Created learning\rendering\train_config.local.json"
  Write-Host "[SETUP] Edit local trainer/model/ComfyUI paths, then run this command again."
  exit 2
}

$Args = @("src\rendering_learning.py", $Action, "--config", "learning\rendering\train_config.local.json")
if ($Action -eq "publish" -and $Activate) {
  $Args += "--activate"
}

python @Args
