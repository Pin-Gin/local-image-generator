param(
  [string]$ComfyUIRoot = "C:\Users\shift\Downloads\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ComfyAppRoot = Join-Path $ComfyUIRoot "ComfyUI"
$Python = Join-Path $ComfyUIRoot "python_embeded\python.exe"
$CustomNodesRoot = Join-Path $ComfyAppRoot "custom_nodes"
$NodeRoot = Join-Path $CustomNodesRoot "comfyui-ipadapter"
$NodeRepo = "https://github.com/comfyorg/comfyui-ipadapter.git"
$NodePinnedCommit = "b188a6cb39b512a9c6da7235b880af42c78ccd0d"

$IPAdapterTarget = Join-Path $RepoRoot "models\ipadapter\ip-adapter-plus_sdxl_vit-h.safetensors"
$IPAdapterUrl = "https://huggingface.co/h94/IP-Adapter/resolve/main/sdxl_models/ip-adapter-plus_sdxl_vit-h.safetensors"
$ClipVisionTarget = Join-Path $RepoRoot "models\clip_vision\CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"
$ClipVisionUrl = "https://huggingface.co/h94/IP-Adapter/resolve/main/models/image_encoder/model.safetensors"

function Invoke-GitChecked {
  param([string[]]$GitArgs)
  & git @GitArgs
  if ($LASTEXITCODE -ne 0) {
    throw "git failed: git $($GitArgs -join ' ')"
  }
}

function Download-Asset {
  param(
    [string]$Url,
    [string]$Target,
    [long]$MinimumBytes
  )

  $Parent = Split-Path -Parent $Target
  New-Item -ItemType Directory -Force -Path $Parent | Out-Null

  if (Test-Path -LiteralPath $Target -PathType Leaf) {
    $ExistingSize = (Get-Item -LiteralPath $Target).Length
    if ($ExistingSize -ge $MinimumBytes) {
      $Hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Target).Hash
      Write-Host "[IPADAPTER:ASSET:ALREADY-PRESENT] $Target"
      Write-Host "[IPADAPTER:ASSET:SHA256] $Hash"
      return
    }
    Remove-Item -LiteralPath $Target -Force
  }

  $Partial = "$Target.part"
  $CurlArgs = @(
    "--fail",
    "--location",
    "--retry", "8",
    "--retry-all-errors",
    "--retry-delay", "5"
  )
  if (Test-Path -LiteralPath $Partial -PathType Leaf) {
    $CurlArgs += @("--continue-at", "-")
  }
  $CurlArgs += @("--output", $Partial, $Url)

  Write-Host "[IPADAPTER:ASSET:DOWNLOAD] $Target"
  & curl.exe @CurlArgs
  if ($LASTEXITCODE -ne 0) {
    throw "download failed: $Url"
  }

  $Size = (Get-Item -LiteralPath $Partial).Length
  if ($Size -lt $MinimumBytes) {
    throw "downloaded asset is unexpectedly small: $Partial ($Size bytes)"
  }

  Move-Item -LiteralPath $Partial -Destination $Target -Force
  $Hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Target).Hash
  Write-Host "[IPADAPTER:ASSET:OK] $Target"
  Write-Host "[IPADAPTER:ASSET:SHA256] $Hash"
}

if (-not (Test-Path -LiteralPath $ComfyAppRoot -PathType Container)) {
  throw "ComfyUI application directory was not found: $ComfyAppRoot"
}
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
  throw "ComfyUI embedded Python was not found: $Python"
}
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  throw "git was not found in PATH"
}
if (-not (Get-Command curl.exe -ErrorAction SilentlyContinue)) {
  throw "curl.exe was not found in PATH"
}

New-Item -ItemType Directory -Force -Path $CustomNodesRoot | Out-Null

if (Test-Path -LiteralPath $NodeRoot -PathType Container) {
  $GitDir = Join-Path $NodeRoot ".git"
  if (-not (Test-Path -LiteralPath $GitDir -PathType Container)) {
    throw "IP-Adapter custom-node directory exists but is not a Git checkout: $NodeRoot"
  }
  $Origin = (& git -C $NodeRoot remote get-url origin).Trim()
  if ($LASTEXITCODE -ne 0 -or ($Origin -notmatch "comfyorg/comfyui-ipadapter" -and $Origin -notmatch "cubiq/ComfyUI_IPAdapter_plus")) {
    throw "unexpected IP-Adapter custom-node origin: $Origin"
  }
  $Dirty = & git -C $NodeRoot status --porcelain
  if ($LASTEXITCODE -ne 0) {
    throw "could not inspect IP-Adapter custom-node working tree"
  }
  if ($Dirty) {
    throw "IP-Adapter custom-node checkout has local changes; refusing to overwrite them"
  }
  Invoke-GitChecked @("-C", $NodeRoot, "fetch", "origin", $NodePinnedCommit)
} else {
  Invoke-GitChecked @("clone", "--no-tags", $NodeRepo, $NodeRoot)
}

Invoke-GitChecked @("-C", $NodeRoot, "checkout", "--detach", $NodePinnedCommit)
$ActualCommit = (& git -C $NodeRoot rev-parse HEAD).Trim()
if ($ActualCommit -ne $NodePinnedCommit) {
  throw "IP-Adapter custom-node commit mismatch: expected=$NodePinnedCommit actual=$ActualCommit"
}
Write-Host "[IPADAPTER:NODE:PINNED] $ActualCommit"

# Do not replace ComfyUI's Torch stack. Basic IP-Adapter uses the existing
# ComfyUI/PyTorch/TorchVision environment; FaceID/InsightFace is intentionally
# not part of this experiment.
& $Python -s -c "import torch, torchvision; print(torch.__version__); print(torchvision.__version__); print('cuda=' + str(torch.cuda.is_available()))"
if ($LASTEXITCODE -ne 0) {
  throw "ComfyUI embedded PyTorch/TorchVision is not importable"
}
Write-Host "[IPADAPTER:PYTORCH:PRESERVED]"

# Add project-owned ipadapter + clip_vision directories to extra_model_paths.yaml.
& (Join-Path $RepoRoot "configure_comfyui_models.ps1") -ComfyUIRoot $ComfyUIRoot
if ($LASTEXITCODE -ne 0) {
  throw "configure_comfyui_models.ps1 failed"
}

Download-Asset -Url $IPAdapterUrl -Target $IPAdapterTarget -MinimumBytes 100000000
Download-Asset -Url $ClipVisionUrl -Target $ClipVisionTarget -MinimumBytes 500000000

Write-Host "[IPADAPTER:INSTALL:OK]"
Write-Host "[NEXT] Fully restart ComfyUI, then run .\tools\python312\python.exe .\tests\capabilities\ipadapter_capability_test.py"
