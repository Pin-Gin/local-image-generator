param(
  [string]$ComfyUIRoot = "C:\Users\shift\Downloads\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ModelRoot = Join-Path $RepoRoot "models"
$ComfyAppRoot = Join-Path $ComfyUIRoot "ComfyUI"
$Target = Join-Path $ComfyAppRoot "extra_model_paths.yaml"

if (-not (Test-Path -LiteralPath $ComfyAppRoot -PathType Container)) {
  throw "ComfyUI application directory was not found: $ComfyAppRoot"
}

$ModelDirs = @(
  "checkpoints",
  "loras",
  "controlnet",
  "upscale_models",
  "vae",
  "clip_vision",
  "ipadapter"
)
foreach ($name in $ModelDirs) {
  New-Item -ItemType Directory -Force -Path (Join-Path $ModelRoot $name) | Out-Null
}

$BasePath = $ModelRoot.Replace("\", "/")
$Block = @"
local_rag:
  base_path: $BasePath
  checkpoints: checkpoints
  loras: loras
  controlnet: controlnet
  upscale_models: upscale_models
  vae: vae
  clip_vision: clip_vision
  ipadapter: ipadapter
"@

$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

if (Test-Path -LiteralPath $Target -PathType Leaf) {
  $Existing = [System.IO.File]::ReadAllText($Target, [System.Text.Encoding]::UTF8)
  if ($Existing -match "(?m)^local_rag:\s*$") {
    if ($Existing.Contains($Block.Trim())) {
      Write-Host "[COMFYUI:MODEL-PATH:ALREADY-CONFIGURED] $Target"
    } else {
      $Pattern = '(?ms)^local_rag:\s*\r?\n(?:^[ \t].*\r?\n?)*'
      if ($Existing -notmatch $Pattern) {
        throw "extra_model_paths.yaml contains local_rag but its block could not be parsed safely: $Target"
      }
      $Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
      $Backup = "$Target.local-rag-backup-$Stamp"
      Copy-Item -LiteralPath $Target -Destination $Backup
      $Updated = [regex]::Replace($Existing, $Pattern, $Block.Trim() + "`r`n", 1)
      [System.IO.File]::WriteAllText($Target, $Updated, $Utf8NoBom)
      Write-Host "[COMFYUI:MODEL-PATH:BACKUP] $Backup"
      Write-Host "[COMFYUI:MODEL-PATH:UPDATED] $Target"
    }
  } else {
    $Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $Backup = "$Target.local-rag-backup-$Stamp"
    Copy-Item -LiteralPath $Target -Destination $Backup
    $Prefix = $Existing.TrimEnd("`r", "`n")
    $Updated = $Prefix + "`r`n`r`n" + $Block.Trim() + "`r`n"
    [System.IO.File]::WriteAllText($Target, $Updated, $Utf8NoBom)
    Write-Host "[COMFYUI:MODEL-PATH:BACKUP] $Backup"
    Write-Host "[COMFYUI:MODEL-PATH:CONFIGURED] $Target"
  }
} else {
  [System.IO.File]::WriteAllText($Target, $Block.Trim() + "`r`n", $Utf8NoBom)
  Write-Host "[COMFYUI:MODEL-PATH:CONFIGURED] $Target"
}

$Checkpoint = Join-Path $ModelRoot "checkpoints\sd_xl_base_1.0.safetensors"
if (Test-Path -LiteralPath $Checkpoint -PathType Leaf) {
  $Hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Checkpoint).Hash
  Write-Host "[MODEL:CHECKPOINT:FOUND] $Checkpoint"
  Write-Host "[MODEL:CHECKPOINT:SHA256] $Hash"
} else {
  Write-Host "[MODEL:CHECKPOINT:WARN] sd_xl_base_1.0.safetensors was not found under project models/checkpoints"
}

Write-Host "[NEXT] Restart ComfyUI after model-path changes so new model categories are reloaded."
