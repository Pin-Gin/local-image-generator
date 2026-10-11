param(
  [ValidateSet("start", "status", "reset-schema", "rotate-app-password", "stop")]
  [string]$Action = "status"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

$EnvFile = Join-Path $RepoRoot ".env.local-ai"
$ComposeFile = Join-Path $RepoRoot "infra\oracle\docker-compose.yml"
$SchemaFile = Join-Path $RepoRoot "infra\oracle\sql\001_fresh_schema.sql"
$ContainerName = "local-rag-oracle"

function Read-LocalEnv([string]$Path) {
  if (-not (Test-Path $Path)) {
    throw ".env.local-ai was not found. Run setup_local_tools.ps1 first."
  }
  $values = @{}
  foreach ($line in Get-Content -LiteralPath $Path -Encoding UTF8) {
    $trimmed = $line.Trim()
    if (-not $trimmed -or $trimmed.StartsWith("#") -or -not $trimmed.Contains("=")) { continue }
    $parts = $trimmed.Split("=", 2)
    $values[$parts[0].Trim()] = $parts[1].Trim().Trim('"').Trim("'")
  }
  return $values
}

function Write-LocalEnvValue([string]$Path, [string]$Key, [string]$Value) {
  $encoding = New-Object System.Text.UTF8Encoding($false)
  $content = [System.IO.File]::ReadAllText($Path, [System.Text.Encoding]::UTF8)
  $pattern = "(?m)^" + [regex]::Escape($Key) + "=.*$"
  if (-not [regex]::IsMatch($content, $pattern)) {
    throw "Required environment key was not found: $Key"
  }
  $replacement = "$Key=$Value"
  $updated = [regex]::Replace($content, $pattern, $replacement, 1)
  [System.IO.File]::WriteAllText($Path, $updated, $encoding)
}

function Require-Docker {
  $cmd = Get-Command docker -ErrorAction SilentlyContinue
  if (-not $cmd) {
    throw "docker was not found. Install Docker Desktop or rerun setup_local_tools.ps1 -InstallSystemTools."
  }
}

function Test-OracleReady([string]$Password) {
  try {
    $probe = "select 1 from dual;`nexit`n"
    $output = $probe | docker exec -i $ContainerName sqlplus -s "system/$Password@//localhost:1521/FREEPDB1" 2>&1
    return (($LASTEXITCODE -eq 0) -and (($output -join "`n") -match "1"))
  } catch {
    return $false
  }
}

function Test-AppReady([string]$Password) {
  try {
    $probe = "select 1 from dual;`nexit`n"
    $output = $probe | docker exec -i $ContainerName sqlplus -s "LOCALRAG_KB1/$Password@//localhost:1521/FREEPDB1" 2>&1
    return (($LASTEXITCODE -eq 0) -and (($output -join "`n") -match "1"))
  } catch {
    return $false
  }
}

function Set-OracleAppPassword([string]$SystemPassword, [string]$NewPassword) {
  $sql = @"
WHENEVER SQLERROR EXIT SQL.SQLCODE
SET ECHO OFF
SET VERIFY OFF
SET FEEDBACK OFF
SET HEADING OFF
ALTER USER LOCALRAG_KB1 IDENTIFIED BY "$NewPassword";
EXIT
"@
  $null = $sql | docker exec -i $ContainerName sqlplus -s "system/$SystemPassword@//localhost:1521/FREEPDB1" 2>&1
  if ($LASTEXITCODE -ne 0) {
    throw "Oracle app password change failed"
  }
}

Require-Docker
$envValues = Read-LocalEnv $EnvFile
$systemPassword = $envValues["LOCALRAG_ORACLE_SYSTEM_PASSWORD"]
$appPassword = $envValues["LOCALRAG_ORACLE_PASSWORD"]
if (-not $systemPassword -or -not $appPassword) {
  throw "Oracle passwords are missing from .env.local-ai."
}

switch ($Action) {
  "start" {
    Write-Host "[ORACLE] Starting local-rag-oracle..."
    docker compose --env-file $EnvFile -f $ComposeFile up -d
    if ($LASTEXITCODE -ne 0) { throw "docker compose up failed" }

    Write-Host "[ORACLE] Waiting for FREEPDB1..."
    $ready = $false
    for ($i = 0; $i -lt 120; $i++) {
      if (Test-OracleReady $systemPassword) {
        $ready = $true
        break
      }
      Start-Sleep -Seconds 3
    }
    if (-not $ready) {
      throw "Oracle did not become ready within 360 seconds. Check: docker logs local-rag-oracle"
    }
    Write-Host "[ORACLE:OK] 127.0.0.1:1521/FREEPDB1"
  }

  "status" {
    docker ps --filter "name=$ContainerName" --format "table {{.Names}}`t{{.Status}}`t{{.Ports}}"
    if (Test-OracleReady $systemPassword) {
      Write-Host "[ORACLE:READY] FREEPDB1"
    } else {
      Write-Host "[ORACLE:NOT-READY]"
      exit 1
    }
  }

  "reset-schema" {
    if (-not (Test-OracleReady $systemPassword)) {
      throw "Oracle is not ready. Run .\oracle_local.ps1 -Action start first."
    }
    $sql = Get-Content -LiteralPath $SchemaFile -Raw -Encoding UTF8
    $sql = $sql.Replace("__APP_PASSWORD__", $appPassword)
    Write-Host "[ORACLE] Recreating LOCALRAG_KB1 from scratch..."
    $sql | docker exec -i $ContainerName sqlplus -s "system/$systemPassword@//localhost:1521/FREEPDB1"
    if ($LASTEXITCODE -ne 0) { throw "Oracle schema reset failed" }
    Write-Host "[ORACLE:SCHEMA:OK] LOCALRAG_KB1"
  }

  "rotate-app-password" {
    if (-not (Test-OracleReady $systemPassword)) {
      throw "Oracle is not ready. Run .\oracle_local.ps1 -Action start first."
    }

    $newPassword = (([guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N")).Substring(0, 32)).ToUpperInvariant()
    Write-Host "[ORACLE] Rotating LOCALRAG_KB1 application password..."

    try {
      Set-OracleAppPassword $systemPassword $newPassword
      if (-not (Test-AppReady $newPassword)) {
        throw "New Oracle app password could not authenticate"
      }
      Write-LocalEnvValue $EnvFile "LOCALRAG_ORACLE_PASSWORD" $newPassword
    } catch {
      try {
        Set-OracleAppPassword $systemPassword $appPassword
      } catch {
        Write-Host "[ORACLE:WARN] Automatic password rollback failed. Manual recovery may be required."
      }
      throw
    }

    Write-Host "[ORACLE:PASSWORD:ROTATED] LOCALRAG_KB1"
    Write-Host "[ORACLE:PASSWORD:OK] .env.local-ai updated without printing the secret"
    Write-Host "[NEXT] Restart ui_server.py/local-RAG processes so they reload .env.local-ai."
  }

  "stop" {
    Write-Host "[ORACLE] Stopping local-rag-oracle..."
    docker compose --env-file $EnvFile -f $ComposeFile down
    if ($LASTEXITCODE -ne 0) { throw "docker compose down failed" }
    Write-Host "[ORACLE:STOPPED]"
  }
}
