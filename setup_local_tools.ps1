param(
  [switch]$InstallSystemTools,
  [switch]$StartOracle
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

function Test-Command([string]$Name) {
  return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Install-WingetPackage([string]$Id) {
  if (-not (Test-Command "winget")) {
    throw "winget is required to install $Id automatically."
  }
  winget install --id $Id -e --source winget --accept-package-agreements --accept-source-agreements
  if ($LASTEXITCODE -ne 0) { throw "winget install failed: $Id" }
}

if (-not (Test-Command "git")) {
  if ($InstallSystemTools) {
    Write-Host "[TOOLS] Installing Git..."
    Install-WingetPackage "Git.Git"
  } else {
    Write-Host "[TOOLS:WARN] git not found. Re-run with -InstallSystemTools to install Git."
  }
} else {
  Write-Host "[TOOLS:OK] git"
}

if (-not (Test-Command "docker")) {
  if ($InstallSystemTools) {
    Write-Host "[TOOLS] Installing Docker Desktop..."
    Install-WingetPackage "Docker.DockerDesktop"
    Write-Host "[TOOLS:INFO] Docker Desktop may require sign-out/reboot and first-run initialization."
  } else {
    Write-Host "[TOOLS:WARN] docker not found. Re-run with -InstallSystemTools to install Docker Desktop."
  }
} else {
  Write-Host "[TOOLS:OK] docker"
}

$Python = $null
$PrivatePython = Join-Path $RepoRoot "tools\python312\python.exe"
if (Test-Path $PrivatePython) {
  $Python = $PrivatePython
} elseif (Test-Command "python") {
  $Python = "python"
} else {
  throw "Python was not found. The project private Python or a system Python is required."
}

Write-Host "[TOOLS] Installing local Python tool dependencies..."
& $Python -m pip install -r (Join-Path $RepoRoot "requirements-local-tools.txt")
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }
Write-Host "[TOOLS:OK] python-oracledb"

$storeDirectories = @(
  "learning\local-ai\store\json-parts",
  "learning\local-ai\store\knowledge",
  "learning\local-ai\store\sources",
  "learning\local-ai\store\staging"
)
foreach ($relative in $storeDirectories) {
  $path = Join-Path $RepoRoot $relative
  New-Item -ItemType Directory -Force -Path $path | Out-Null
}
Write-Host "[STORE:OK] learning\local-ai\store"

$EnvFile = Join-Path $RepoRoot ".env.local-ai"
if (-not (Test-Path $EnvFile)) {
  $systemPassword = ([guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N")).Substring(0, 32)
  $appPassword = ([guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N")).Substring(0, 32)
  $memorielaRoot = ""
  $defaultMemoriela = Join-Path (Split-Path -Parent $RepoRoot) "MEMORIELA"
  if ((Test-Path $defaultMemoriela) -and (Test-Path (Join-Path $defaultMemoriela ".git"))) {
    $memorielaRoot = $defaultMemoriela
  }
  $content = @"
LOCALRAG_ORACLE_DSN=127.0.0.1:1521/FREEPDB1
LOCALRAG_ORACLE_USER=LOCALRAG_KB1
LOCALRAG_ORACLE_PASSWORD=$appPassword
LOCALRAG_ORACLE_SYSTEM_PASSWORD=$systemPassword
LOCALRAG_MEMORIELA_ROOT=$memorielaRoot
"@
  [System.IO.File]::WriteAllText($EnvFile, $content, (New-Object System.Text.UTF8Encoding($false)))
  Write-Host "[ENV:CREATED] .env.local-ai"
  if ($memorielaRoot) {
    Write-Host "[GIT:OK] MEMORIELA=$memorielaRoot"
  }
} else {
  Write-Host "[ENV:OK] .env.local-ai already exists"
}

if ($StartOracle) {
  if (-not (Test-Command "docker")) {
    throw "docker is not available in this shell. Start/restart Docker Desktop, then rerun."
  }
  & powershell.exe -ExecutionPolicy Bypass -File (Join-Path $RepoRoot "oracle_local.ps1") -Action start
  if ($LASTEXITCODE -ne 0) { throw "Oracle start failed" }
  & powershell.exe -ExecutionPolicy Bypass -File (Join-Path $RepoRoot "oracle_local.ps1") -Action reset-schema
  if ($LASTEXITCODE -ne 0) { throw "Oracle schema setup failed" }
}

Write-Host "[LOCAL-TOOLS:SETUP:OK]"
Write-Host "[NEXT] If MEMORIELA was not auto-detected, set LOCALRAG_MEMORIELA_ROOT in .env.local-ai."
