param(
  [string]$ComfyUIRoot = "$env:USERPROFILE\Downloads\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable\ComfyUI",
  [switch]$SkipDependencyInstall
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

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
& $PythonExe --version

if (-not (Test-Path (Join-Path $TrainerRoot ".git"))) {
  if (Test-Path $TrainerRoot) {
    throw "tools\sd-scripts exists but is not a Git repository. Remove or rename it before setup."
  }
  Write-Host "[SETUP] Cloning kohya-ss/sd-scripts into tools\sd-scripts ..."
  git clone --depth 1 https://github.com/kohya-ss/sd-scripts.git $TrainerRoot
} else {
  Write-Host "[SETUP] Updating tools\sd-scripts ..."
  git -C $TrainerRoot pull --ff-only
}

if (-not (Test-Path $TrainerVenvPython)) {
  Write-Host "[SETUP] Creating sd-scripts virtual environment ..."
  & $PythonExe -m venv (Join-Path $TrainerRoot "venv")
}

if (-not $SkipDependencyInstall) {
  Write-Host "[SETUP] Updating pip ..."
  & $TrainerVenvPython -m pip install --upgrade pip setuptools wheel

  Write-Host "[SETUP] Installing RTX 50-series PyTorch (CUDA 12.8) ..."
  & $TrainerVenvPython -m pip install torch==2.8.0 torchvision==0.23.0 torchaudio==2.8.0 --index-url $TorchIndex

  Write-Host "[SETUP] Installing sd-scripts requirements ..."
  & $TrainerVenvPython -m pip install --upgrade -r (Join-Path $TrainerRoot "requirements.txt")
}

Write-Host "[SETUP] Verifying CUDA visibility ..."
& $TrainerVenvPython -c "import torch; print('torch=' + torch.__version__); print('cuda=' + str(torch.cuda.is_available())); print('device=' + (torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NONE'))"
if ($LASTEXITCODE -ne 0) {
  throw "PyTorch verification failed."
}

if (-not (Test-Path $Checkpoint)) {
  throw "SDXL base checkpoint not found: $Checkpoint"
}
New-Item -ItemType Directory -Force -Path $LoraRoot | Out-Null

if (-not (Test-Path $LocalConfig)) {
  Copy-Item $ExampleConfig $LocalConfig
}

$config = Get-Content $LocalConfig -Raw | ConvertFrom-Json
$config.trainer.repo = ($TrainerRoot -replace '\\', '/')
$config.trainer.python_executable = ($TrainerVenvPython -replace '\\', '/')
$config.trainer.accelerate_config = ((Join-Path $RepoRoot "learning\rendering\accelerate_config.yaml") -replace '\\', '/')
$config.model.pretrained_model_name_or_path = ($Checkpoint -replace '\\', '/')
$config.output.comfyui_lora_directory = ($LoraRoot -replace '\\', '/')
$config | ConvertTo-Json -Depth 20 | Set-Content $LocalConfig -Encoding UTF8

Write-Host "[SETUP:OK] trainer=$TrainerRoot"
Write-Host "[SETUP:OK] python=$TrainerVenvPython"
Write-Host "[SETUP:OK] checkpoint=$Checkpoint"
Write-Host "[SETUP:OK] config=$LocalConfig"
Write-Host "[NEXT] Put rendering training images/captions under learning\rendering\dataset\20_mdanime and run train_rendering.ps1 -Action validate"
