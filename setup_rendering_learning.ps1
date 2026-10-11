param(
  [string]$ComfyUIRoot = "$env:USERPROFILE\Downloads\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable\ComfyUI",
  [switch]$SkipDependencyInstall
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

function Invoke-Checked {
  param(
    [Parameter(Mandatory=$true)][string]$FilePath,
    [Parameter(ValueFromRemainingArguments=$true)][string[]]$Arguments
  )
  & $FilePath @Arguments
  if ($LASTEXITCODE -ne 0) {
    throw "Command failed ($LASTEXITCODE): $FilePath $($Arguments -join ' ')"
  }
}

$ToolsRoot = Join-Path $RepoRoot "tools"
$PythonRoot = Join-Path $ToolsRoot "python312"
$PythonExe = Join-Path $PythonRoot "python.exe"
$TrainerRoot = Join-Path $ToolsRoot "sd-scripts"
$TrainerVenvPython = Join-Path $TrainerRoot "venv\Scripts\python.exe"
$DownloadRoot = Join-Path $ToolsRoot "_downloads"
$PythonInstaller = Join-Path $DownloadRoot "python-3.12.10-amd64.exe"
$PythonInstallerUrl = "https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe"
$TorchIndex = "https://download.pytorch.org/whl/cu128"
$LocalConfig = Join-Path $RepoRoot "learning\rendering\train_config.local.json"
$ExampleConfig = Join-Path $RepoRoot "learning\rendering\train_config.example.json"
$Checkpoint = Join-Path $ComfyUIRoot "models\checkpoints\sd_xl_base_1.0.safetensors"
$LoraRoot = Join-Path $ComfyUIRoot "models\loras"
$AccelerateConfig = Join-Path $RepoRoot "learning\rendering\accelerate_config.yaml"

New-Item -ItemType Directory -Force -Path $ToolsRoot | Out-Null
New-Item -ItemType Directory -Force -Path $DownloadRoot | Out-Null

if (-not (Test-Path $PythonExe)) {
  Write-Host "[SETUP] Installing private Python 3.12.10 under tools\python312 ..."
  if (-not (Test-Path $PythonInstaller)) {
    Invoke-WebRequest -Uri $PythonInstallerUrl -OutFile $PythonInstaller
  }
  $arguments = @(
    "/quiet",
    "InstallAllUsers=0",
    "TargetDir=$PythonRoot",
    "PrependPath=0",
    "Include_launcher=0",
    "Include_test=0",
    "Include_doc=0",
    "Include_tcltk=0",
    "Include_pip=1"
  )
  $process = Start-Process -FilePath $PythonInstaller -ArgumentList $arguments -Wait -PassThru
  if ($process.ExitCode -ne 0 -or -not (Test-Path $PythonExe)) {
    throw "Private Python installation failed. exit=$($process.ExitCode) expected=$PythonExe"
  }
}

Write-Host "[SETUP] Python: $PythonExe"
Invoke-Checked $PythonExe "--version"

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  throw "Git is required but was not found in PATH."
}

if (-not (Test-Path (Join-Path $TrainerRoot ".git"))) {
  if (Test-Path $TrainerRoot) {
    throw "tools\sd-scripts exists but is not a Git repository. Remove or rename it before setup."
  }
  Write-Host "[SETUP] Cloning kohya-ss/sd-scripts into tools\sd-scripts ..."
  Invoke-Checked "git" "clone" "--depth" "1" "https://github.com/kohya-ss/sd-scripts.git" $TrainerRoot
} else {
  Write-Host "[SETUP] Updating tools\sd-scripts ..."
  Invoke-Checked "git" "-C" $TrainerRoot "pull" "--ff-only"
}

if (-not (Test-Path $TrainerVenvPython)) {
  Write-Host "[SETUP] Creating sd-scripts virtual environment ..."
  Invoke-Checked $PythonExe "-m" "venv" (Join-Path $TrainerRoot "venv")
}

if (-not $SkipDependencyInstall) {
  Write-Host "[SETUP] Updating pip ..."
  Invoke-Checked $TrainerVenvPython "-m" "pip" "install" "--upgrade" "pip" "setuptools" "wheel"

  Write-Host "[SETUP] Installing RTX 50-series PyTorch (CUDA 12.8) ..."
  Invoke-Checked $TrainerVenvPython "-m" "pip" "install" "torch==2.8.0" "torchvision==0.23.0" "torchaudio==2.8.0" "--index-url" $TorchIndex

  Write-Host "[SETUP] Installing sd-scripts requirements ..."
  Invoke-Checked $TrainerVenvPython "-m" "pip" "install" "--upgrade" "-r" (Join-Path $TrainerRoot "requirements.txt")
}

Write-Host "[SETUP] Verifying CUDA visibility ..."
Invoke-Checked $TrainerVenvPython "-c" "import torch; print('torch=' + torch.__version__); print('cuda=' + str(torch.cuda.is_available())); print('device=' + (torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NONE')); raise SystemExit(0 if torch.cuda.is_available() else 3)"

if (-not (Test-Path $Checkpoint)) {
  throw "SDXL base checkpoint not found: $Checkpoint"
}
if (-not (Test-Path $AccelerateConfig)) {
  throw "Accelerate config not found: $AccelerateConfig"
}
New-Item -ItemType Directory -Force -Path $LoraRoot | Out-Null

if (-not (Test-Path $LocalConfig)) {
  Copy-Item $ExampleConfig $LocalConfig
}

$config = Get-Content $LocalConfig -Raw | ConvertFrom-Json
$config.trainer.repo = ($TrainerRoot -replace '\\', '/')
$config.trainer.python_executable = ($TrainerVenvPython -replace '\\', '/')
$config.trainer.accelerate_config = ($AccelerateConfig -replace '\\', '/')
$config.model.pretrained_model_name_or_path = ($Checkpoint -replace '\\', '/')
$config.output.comfyui_lora_directory = ($LoraRoot -replace '\\', '/')
$json = $config | ConvertTo-Json -Depth 20
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($LocalConfig, $json + [Environment]::NewLine, $utf8NoBom)

Write-Host "[SETUP:OK] trainer=$TrainerRoot"
Write-Host "[SETUP:OK] python=$TrainerVenvPython"
Write-Host "[SETUP:OK] checkpoint=$Checkpoint"
Write-Host "[SETUP:OK] config=$LocalConfig"
Write-Host "[NEXT] Put rendering training images/captions under learning\rendering\dataset\20_mdanime and run train_rendering.ps1 -Action validate"
