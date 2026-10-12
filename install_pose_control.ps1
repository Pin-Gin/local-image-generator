param(
  [string]$ComfyUIRoot = "C:\Users\shift\Downloads\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ComfyAppRoot = Join-Path $ComfyUIRoot "ComfyUI"
$Python = Join-Path $ComfyUIRoot "python_embeded\python.exe"
$CustomNodesRoot = Join-Path $ComfyAppRoot "custom_nodes"
$AuxRoot = Join-Path $CustomNodesRoot "comfyui_controlnet_aux"
$AuxRepo = "https://github.com/Fannovel16/comfyui_controlnet_aux.git"
$AuxPinnedCommit = "a587a4c1594524c1d2de5cd1a86cd868ff448e1c"

$ControlNetTarget = Join-Path $RepoRoot "models\controlnet\SDXL\controlnet-openpose-sdxl-1.0\diffusion_pytorch_model.safetensors"
$ControlNetUrl = "https://huggingface.co/xinsir/controlnet-openpose-sdxl-1.0/resolve/main/diffusion_pytorch_model.safetensors"

$DWPoseBboxTarget = Join-Path $AuxRoot "ckpts\yzd-v\DWPose\yolox_l.onnx"
$DWPoseBboxUrl = "https://huggingface.co/yzd-v/DWPose/resolve/main/yolox_l.onnx"
$DWPoseEstimatorTarget = Join-Path $AuxRoot "ckpts\hr16\DWPose-TorchScript-BatchSize5\dw-ll_ucoco_384_bs5.torchscript.pt"
$DWPoseEstimatorUrl = "https://huggingface.co/hr16/DWPose-TorchScript-BatchSize5/resolve/main/dw-ll_ucoco_384_bs5.torchscript.pt"

function Invoke-GitChecked {
  param([string[]]$GitArgs)
  & git @GitArgs
  if ($LASTEXITCODE -ne 0) {
    throw "git failed: git $($GitArgs -join ' ')"
  }
}

function Test-PythonModule {
  param([string]$Module)

  # Windows PowerShell can promote native stderr into a terminating error when
  # $ErrorActionPreference is Stop. Temporarily relax it so a normal ImportError
  # is handled through the process exit code instead of aborting this installer.
  $PreviousPreference = $ErrorActionPreference
  try {
    $ErrorActionPreference = "Continue"
    & $Python -s -c "import importlib; importlib.import_module('$Module')" 2>$null
    $ExitCode = $LASTEXITCODE
  }
  finally {
    $ErrorActionPreference = $PreviousPreference
  }

  return ($ExitCode -eq 0)
}

function Ensure-PythonModule {
  param(
    [string]$Module,
    [string]$Package
  )

  Write-Host "[POSE:PYTHON-MODULE:CHECK] $Module"
  if (Test-PythonModule $Module) {
    Write-Host "[POSE:PYTHON-MODULE:OK] $Module"
    return
  }

  Write-Host "[POSE:PYTHON-MODULE:INSTALL] $Package"
  & $Python -s -m pip install $Package
  if ($LASTEXITCODE -ne 0) {
    throw "pip install failed for $Package"
  }

  if (-not (Test-PythonModule $Module)) {
    throw "Python module still unavailable after install: $Module"
  }
  Write-Host "[POSE:PYTHON-MODULE:OK] $Module"
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
      Write-Host "[POSE:ASSET:ALREADY-PRESENT] $Target"
      Write-Host "[POSE:ASSET:SHA256] $Hash"
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

  Write-Host "[POSE:ASSET:DOWNLOAD] $Target"
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
  Write-Host "[POSE:ASSET:OK] $Target"
  Write-Host "[POSE:ASSET:SHA256] $Hash"
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

if (Test-Path -LiteralPath $AuxRoot -PathType Container) {
  $GitDir = Join-Path $AuxRoot ".git"
  if (-not (Test-Path -LiteralPath $GitDir -PathType Container)) {
    throw "custom node directory exists but is not a Git checkout: $AuxRoot"
  }
  $Origin = (& git -C $AuxRoot remote get-url origin).Trim()
  if ($LASTEXITCODE -ne 0 -or $Origin -notmatch "Fannovel16/comfyui_controlnet_aux") {
    throw "unexpected comfyui_controlnet_aux origin: $Origin"
  }
  $Dirty = & git -C $AuxRoot status --porcelain
  if ($LASTEXITCODE -ne 0) {
    throw "could not inspect comfyui_controlnet_aux working tree"
  }
  if ($Dirty) {
    throw "comfyui_controlnet_aux has local changes; refusing to overwrite them"
  }
  Invoke-GitChecked @("-C", $AuxRoot, "fetch", "origin", $AuxPinnedCommit)
} else {
  Invoke-GitChecked @("clone", "--no-tags", $AuxRepo, $AuxRoot)
}

Invoke-GitChecked @("-C", $AuxRoot, "checkout", "--detach", $AuxPinnedCommit)
$ActualCommit = (& git -C $AuxRoot rev-parse HEAD).Trim()
if ($ActualCommit -ne $AuxPinnedCommit) {
  throw "comfyui_controlnet_aux commit mismatch: expected=$AuxPinnedCommit actual=$ActualCommit"
}
Write-Host "[POSE:DWPOSE-NODE:PINNED] $ActualCommit"

# Preserve ComfyUI's existing Torch/TorchVision build. Install only modules required by the DWPose path when absent.
& $Python -s -c "import torch; print(torch.__version__); print('cuda=' + str(torch.cuda.is_available()))"
if ($LASTEXITCODE -ne 0) {
  throw "ComfyUI embedded PyTorch is not importable"
}
Write-Host "[POSE:PYTORCH:PRESERVED]"

Ensure-PythonModule "importlib_metadata" "importlib_metadata"
Ensure-PythonModule "huggingface_hub" "huggingface_hub"
Ensure-PythonModule "scipy" "scipy"
Ensure-PythonModule "cv2" "opencv-python>=4.7.0.72"
Ensure-PythonModule "filelock" "filelock"
Ensure-PythonModule "numpy" "numpy"
Ensure-PythonModule "PIL" "Pillow"
Ensure-PythonModule "einops" "einops"
Ensure-PythonModule "yaml" "pyyaml"

# Use the extension's current default DWPose path: OpenCV-capable YOLOX bbox + TorchScript pose estimator.
Download-Asset -Url $DWPoseBboxUrl -Target $DWPoseBboxTarget -MinimumBytes 1000000
Download-Asset -Url $DWPoseEstimatorUrl -Target $DWPoseEstimatorTarget -MinimumBytes 1000000

# SDXL OpenPose ControlNet kept under local-RAG's project-owned model root.
Download-Asset -Url $ControlNetUrl -Target $ControlNetTarget -MinimumBytes 2000000000

Write-Host "[POSE:INSTALL:OK]"
Write-Host "[NEXT] Restart ComfyUI, then run .\tools\python312\python.exe .\tests\capabilities\pose_control_capability_test.py"
