<#
  AutoRisk launcher.

  Usage (from the autorisk-app folder):
    .\run.ps1              # same as "start"
    .\run.ps1 start        # backend + frontend in two new windows, opens the browser
    .\run.ps1 setup        # install / update all dependencies (safe to re-run)
    .\run.ps1 backend      # run only the FastAPI backend in this window
    .\run.ps1 frontend     # run only the React frontend in this window
    .\run.ps1 reset-db     # WIPE the database and reload schema.sql + seed.sql
    .\run.ps1 help

  If PowerShell refuses to run scripts, use run.bat instead (same arguments).
#>
param(
    [ValidateSet("start", "setup", "backend", "frontend", "reset-db", "help")]
    [string]$Command = "start"
)

$ErrorActionPreference = "Stop"
$Root        = $PSScriptRoot
$Backend     = Join-Path $Root "backend"
$Frontend    = Join-Path $Root "frontend"
$VenvPython  = Join-Path $Backend ".venv\Scripts\python.exe"

function Write-Step($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }

function Test-Tool($name, $hint) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        throw "'$name' was not found on PATH. $hint"
    }
}

function Test-PortFree($port) {
    $busy = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($busy) {
        Write-Host "Port $port is already in use - is AutoRisk already running?" -ForegroundColor Yellow
        return $false
    }
    return $true
}

function Invoke-Setup {
    Test-Tool "python" "Install Python 3.10+ from python.org."
    Test-Tool "npm"    "Install Node.js 18+ from nodejs.org."

    if (-not (Test-Path $VenvPython)) {
        Write-Step "Creating Python virtual environment (backend\.venv)"
        python -m venv (Join-Path $Backend ".venv")
    }
    Write-Step "Installing backend dependencies"
    & $VenvPython -m pip install --quiet -r (Join-Path $Backend "requirements.txt")
    if ($LASTEXITCODE -ne 0) { throw "pip install failed" }

    $envFile = Join-Path $Backend ".env"
    if (-not (Test-Path $envFile)) {
        Copy-Item (Join-Path $Backend ".env.example") $envFile
        Write-Host "Created backend\.env from .env.example - edit DATABASE_URL in it." -ForegroundColor Yellow
    }

    Write-Step "Installing frontend dependencies"
    Push-Location $Frontend
    try { npm install; if ($LASTEXITCODE -ne 0) { throw "npm install failed" } }
    finally { Pop-Location }

    Write-Step "Setup complete. Run: .\run.ps1 start"
}

function Assert-Installed {
    if (-not (Test-Path $VenvPython) -or -not (Test-Path (Join-Path $Frontend "node_modules"))) {
        Write-Step "Dependencies missing - running setup first"
        Invoke-Setup
    }
}

function Start-Backend {
    Write-Step "Backend: http://localhost:8000  (API docs: /docs)  - Ctrl+C to stop"
    Push-Location $Backend
    try { & $VenvPython -m uvicorn app.main:app --reload --port 8000 }
    finally { Pop-Location }
}

function Start-Frontend {
    Write-Step "Frontend: http://localhost:5173  - Ctrl+C to stop"
    Push-Location $Frontend
    try { npm run dev }
    finally { Pop-Location }
}

function Start-All {
    Assert-Installed
    $self = Join-Path $Root "run.ps1"

    if (Test-PortFree 8000) {
        Write-Step "Opening backend window"
        Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "`"$self`"", "backend"
    }
    if (Test-PortFree 5173) {
        Write-Step "Opening frontend window"
        Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "`"$self`"", "frontend"
    }

    Write-Step "Waiting for the frontend to come up..."
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1
        if (Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue) { break }
    }
    Start-Process "http://localhost:5173"

    Write-Host ""
    Write-Host "AutoRisk is running." -ForegroundColor Green
    Write-Host "  App:      http://localhost:5173"
    Write-Host "  API docs: http://localhost:8000/docs"
    Write-Host "  Login:    admin@autorisk.demo / admin123"
    Write-Host "To stop: press Ctrl+C in each of the two new windows (or just close them)."
}

function Reset-Database {
    Assert-Installed
    Write-Host "This DELETES every table in the database in backend\.env and reloads the demo data." -ForegroundColor Red
    $answer = Read-Host "Type YES to continue"
    if ($answer -ne "YES") { Write-Host "Cancelled."; return }
    Write-Step "Resetting database"
    & $VenvPython (Join-Path $Root "db\reset_db.py")
    if ($LASTEXITCODE -ne 0) { throw "Database reset failed" }
}

switch ($Command) {
    "start"    { Start-All }
    "setup"    { Invoke-Setup }
    "backend"  { Assert-Installed; Start-Backend }
    "frontend" { Assert-Installed; Start-Frontend }
    "reset-db" { Reset-Database }
    "help"     { Get-Content $PSCommandPath -TotalCount 14 | Select-Object -Skip 1 }
}
