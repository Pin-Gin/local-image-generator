param(
  [ValidateSet("learn", "dev", "all")]
  [string]$Role = "learn",
  [string]$OllamaVersion = "v0.34.0",
  [switch]$SkipRuntimeDownload
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ToolsRoot = Join-Path $RepoRoot "tools"
$OllamaRoot = Join-Path $ToolsRoot "ollama"
$ModelsRoot = Join-Path $OllamaRoot "models"
$DownloadsRoot = Join-Path $ToolsRoot "_downloads\ollama"
$OllamaExe = Join-Path $OllamaRoot "ollama.exe"
$ArchivePath = Join-Path $DownloadsRoot "ollama-windows-amd64-$OllamaVersion.zip"
$HostAddress = "127.0.0.1:11435"
$BaseUrl = "http://$HostAddress"

$LearnModel = "qwen3-vl:8b"
$DevModel = "qwen2.5-coder:14b"

function Test-OllamaReady {
  try {
    $null = Invoke-RestMethod -Method Get -Uri "$BaseUrl/api/version" -TimeoutSec 2
    return $true
  }
  catch {
    return $false
  }
}

function Wait-OllamaReady {
  param([int]$TimeoutSeconds = 30)

  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  while ((Get-Date) -lt $deadline) {
    if (Test-OllamaReady) {
      return
    }
    Start-Sleep -Milliseconds 500
  }
  throw "Project-local Ollama did not become ready at $BaseUrl"
}

function Start-ProjectOllama {
  if (Test-OllamaReady) {
    Write-Host "[LOCAL-AI] Ollama already running at $BaseUrl"
    return
  }

  if (-not (Test-Path $OllamaExe)) {
    throw "Project-local Ollama executable not found: $OllamaExe"
  }

  $env:OLLAMA_HOST = $HostAddress
  $env:OLLAMA_MODELS = $ModelsRoot

  Write-Host "[LOCAL-AI] Starting project-local Ollama on $HostAddress ..."
  Start-Process `
    -FilePath $OllamaExe `
    -ArgumentList "serve" `
    -WorkingDirectory $OllamaRoot `
    -WindowStyle Hidden | Out-Null

  Wait-OllamaReady
}

New-Item -ItemType Directory -Force -Path $ToolsRoot | Out-Null
New-Item -ItemType Directory -Force -Path $OllamaRoot | Out-Null
New-Item -ItemType Directory -Force -Path $ModelsRoot | Out-Null
New-Item -ItemType Directory -Force -Path $DownloadsRoot | Out-Null

if (-not (Test-Path $OllamaExe)) {
  if ($SkipRuntimeDownload) {
    throw "Ollama runtime is missing and -SkipRuntimeDownload was supplied: $OllamaExe"
  }

  $downloadUrl = "https://github.com/ollama/ollama/releases/download/$OllamaVersion/ollama-windows-amd64.zip"
  Write-Host "[LOCAL-AI] Downloading Ollama $OllamaVersion ..."
  Write-Host "[LOCAL-AI] $downloadUrl"
  Invoke-WebRequest -Uri $downloadUrl -OutFile $ArchivePath

  Write-Host "[LOCAL-AI] Extracting into tools\ollama ..."
  Expand-Archive -Path $ArchivePath -DestinationPath $OllamaRoot -Force
}
else {
  Write-Host "[LOCAL-AI] Existing runtime: $OllamaExe"
}

if (-not (Test-Path $OllamaExe)) {
  throw "Ollama extraction completed but ollama.exe is missing: $OllamaExe"
}

$env:OLLAMA_HOST = $HostAddress
$env:OLLAMA_MODELS = $ModelsRoot
Start-ProjectOllama

$models = @()
switch ($Role) {
  "learn" { $models = @($LearnModel) }
  "dev" { $models = @($DevModel) }
  "all" { $models = @($LearnModel, $DevModel) }
}

foreach ($model in $models) {
  Write-Host "[LOCAL-AI] Pulling model: $model"
  & $OllamaExe pull $model
  if ($LASTEXITCODE -ne 0) {
    throw "ollama pull failed for $model with exit code $LASTEXITCODE"
  }
}

Write-Host "[LOCAL-AI:SETUP:OK] runtime=$OllamaExe"
Write-Host "[LOCAL-AI:SETUP:OK] models=$ModelsRoot"
Write-Host "[LOCAL-AI:SETUP:OK] api=$BaseUrl"
Write-Host "[LOCAL-AI:SETUP:OK] role=$Role"
Write-Host "[NEXT] powershell -ExecutionPolicy Bypass -File .\local_ai.ps1 -Action verify -Role $Role"
