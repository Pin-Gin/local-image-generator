param(
  [ValidateSet("setup", "start", "status", "verify")]
  [string]$Action = "status",
  [ValidateSet("learn", "dev", "all")]
  [string]$Role = "learn",
  [string]$Prompt = "短く自己紹介してください。",
  [string]$Image = ""
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$OllamaRoot = Join-Path $RepoRoot "tools\ollama"
$ModelsRoot = Join-Path $OllamaRoot "models"
$OllamaExe = Join-Path $OllamaRoot "ollama.exe"
$HostAddress = "127.0.0.1:11435"
$BaseUrl = "http://$HostAddress"

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
  $deadline = (Get-Date).AddSeconds(30)
  while ((Get-Date) -lt $deadline) {
    if (Test-OllamaReady) {
      return
    }
    Start-Sleep -Milliseconds 500
  }
  throw "Project-local Ollama did not become ready at $BaseUrl"
}

function Start-LocalAI {
  if (Test-OllamaReady) {
    Write-Host "[LOCAL-AI:OK] already running at $BaseUrl"
    return
  }

  if (-not (Test-Path $OllamaExe)) {
    throw "Local AI runtime is not installed. Run: powershell -ExecutionPolicy Bypass -File .\local_ai.ps1 -Action setup -Role learn"
  }

  New-Item -ItemType Directory -Force -Path $ModelsRoot | Out-Null
  $env:OLLAMA_HOST = $HostAddress
  $env:OLLAMA_MODELS = $ModelsRoot

  Start-Process `
    -FilePath $OllamaExe `
    -ArgumentList "serve" `
    -WorkingDirectory $OllamaRoot `
    -WindowStyle Hidden | Out-Null

  Wait-OllamaReady
  Write-Host "[LOCAL-AI:OK] started at $BaseUrl"
}

Set-Location $RepoRoot

switch ($Action) {
  "setup" {
    & powershell -ExecutionPolicy Bypass -File .\setup_local_ai.ps1 -Role $Role
    if ($LASTEXITCODE -ne 0) {
      exit $LASTEXITCODE
    }
    break
  }

  "start" {
    Start-LocalAI
    break
  }

  "status" {
    if (-not (Test-OllamaReady)) {
      Write-Host "[LOCAL-AI:OFFLINE] $BaseUrl"
      exit 2
    }
    $version = Invoke-RestMethod -Method Get -Uri "$BaseUrl/api/version" -TimeoutSec 5
    $tags = Invoke-RestMethod -Method Get -Uri "$BaseUrl/api/tags" -TimeoutSec 10
    Write-Host "[LOCAL-AI:OK] api=$BaseUrl"
    if ($null -ne $version.version) {
      Write-Host "[LOCAL-AI:OK] version=$($version.version)"
    }
    foreach ($model in $tags.models) {
      Write-Host "[LOCAL-AI:MODEL] $($model.name)"
    }
    break
  }

  "verify" {
    if ($Role -eq "all") {
      throw "verify requires -Role learn or -Role dev"
    }
    Start-LocalAI
    $python = Join-Path $RepoRoot "tools\python312\python.exe"
    if (-not (Test-Path $python)) {
      $python = "python"
    }

    $args = @("src\local_ai_smoke.py", "--role", $Role, "--prompt", $Prompt)
    if ($Image) {
      $args += @("--image", $Image)
    }
    & $python @args
    exit $LASTEXITCODE
  }
}
