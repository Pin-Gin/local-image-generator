param(
  [string]$ComfyUIRoot = "C:\Users\shift\Downloads\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable"
)

$ErrorActionPreference = "Stop"
$ComfyAppRoot = Join-Path $ComfyUIRoot "ComfyUI"
$Python = Join-Path $ComfyUIRoot "python_embeded\python.exe"
$AuxRoot = Join-Path $ComfyAppRoot "custom_nodes\comfyui_controlnet_aux"
$AuxSrc = Join-Path $AuxRoot "src"

if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
  throw "ComfyUI embedded Python was not found: $Python"
}
if (-not (Test-Path -LiteralPath $AuxRoot -PathType Container)) {
  throw "comfyui_controlnet_aux was not found: $AuxRoot"
}

function Test-PythonModule {
  param([string]$Module)
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
  Write-Host "[POSE:DWPOSE-DEPENDENCY:CHECK] $Module"
  if (Test-PythonModule $Module) {
    Write-Host "[POSE:DWPOSE-DEPENDENCY:OK] $Module"
    return
  }

  Write-Host "[POSE:DWPOSE-DEPENDENCY:INSTALL] $Package"
  & $Python -s -m pip install $Package
  if ($LASTEXITCODE -ne 0) {
    throw "pip install failed for $Package"
  }
  if (-not (Test-PythonModule $Module)) {
    throw "Python module still unavailable after install: $Module"
  }
  Write-Host "[POSE:DWPOSE-DEPENDENCY:OK] $Module"
}

# DWPose imports these eagerly through custom_controlnet_aux.dwpose.body/util.
Ensure-PythonModule "matplotlib" "matplotlib"

# torchvision must stay matched to the existing ComfyUI torch build; never replace it automatically.
Write-Host "[POSE:DWPOSE-DEPENDENCY:CHECK] torchvision"
if (-not (Test-PythonModule "torchvision")) {
  throw "torchvision is missing or broken. Refusing to auto-install because it must match ComfyUI's existing torch build."
}
Write-Host "[POSE:DWPOSE-DEPENDENCY:OK] torchvision"

# Probe the exact DWPose core import without loading every optional controlnet_aux wrapper.
$Probe = "import sys; sys.path.insert(0, r'$AuxSrc'); from custom_controlnet_aux.dwpose import DwposeDetector, AnimalposeDetector; print('[POSE:DWPOSE-CORE-IMPORT:OK]')"
$PreviousPreference = $ErrorActionPreference
try {
  $ErrorActionPreference = "Continue"
  & $Python -s -c $Probe
  $ExitCode = $LASTEXITCODE
}
finally {
  $ErrorActionPreference = $PreviousPreference
}
if ($ExitCode -ne 0) {
  throw "DWPose core import still fails. The Python traceback above is the next diagnostic target."
}

Write-Host "[POSE:DWPOSE-REPAIR:OK]"
Write-Host "[NEXT] Restart ComfyUI, then run .\tools\python312\python.exe .\src\pose_control_capability_test.py"
