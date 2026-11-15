<#
  AutoRisk test runner.

  Usage (from the autorisk-app folder):
    .\testing\run_tests.ps1              # same as "all"
    .\testing\run_tests.ps1 unit         # pricing unit tests only (no Docker needed)
    .\testing\run_tests.ps1 api          # API tests (starts the test DB)
    .\testing\run_tests.ps1 e2e          # browser tests (starts the test DB + servers)
    .\testing\run_tests.ps1 all          # everything, plus an HTML report
    .\testing\run_tests.ps1 setup        # install test dependencies + Chromium
    .\testing\run_tests.ps1 db-down      # stop and delete the test database

  Any extra arguments go straight to pytest, e.g.
    .\testing\run_tests.ps1 api -k quote        # only tests with "quote" in the name
    .\testing\run_tests.ps1 api -m security     # only security-marked tests
#>
# No param() block on purpose: PowerShell would try to treat pytest flags
# like -k / -m / -q as parameters of THIS script and fail. Read $args instead.
$Suites = "all", "unit", "api", "e2e", "setup", "db-down"
$Suite = "all"
$PytestArgs = @($args)
if ($args.Count -gt 0 -and $Suites -contains $args[0]) {
    $Suite = $args[0]
    $PytestArgs = @($args | Select-Object -Skip 1)
}

# "Continue", not "Stop": in Windows PowerShell 5.1, harmless warnings that
# docker/pip print on stderr would otherwise abort the script. Failures are
# caught by checking $LASTEXITCODE after each command instead.
$ErrorActionPreference = "Continue"
$Testing = $PSScriptRoot
$Root    = Split-Path $Testing -Parent
$Python  = Join-Path $Root "backend\.venv\Scripts\python.exe"
$Compose = Join-Path $Testing "docker-compose.test.yml"

function Write-Step($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }

if (-not (Test-Path $Python)) {
    throw "backend\.venv not found. Run .\run.ps1 setup first."
}
if (-not (Test-Path (Join-Path $Testing ".env.test"))) {
    Copy-Item (Join-Path $Testing ".env.test.example") (Join-Path $Testing ".env.test")
    Write-Step "Created testing\.env.test"
}

function Start-TestDb {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "Docker not found. Install Docker Desktop (the test database runs in it)."
    }
    docker info *> $null
    if ($LASTEXITCODE -ne 0) { throw "Docker is installed but not running. Start Docker Desktop and retry." }
    Write-Step "Starting test database (port 5544)"
    docker compose -f $Compose up -d --wait
    if ($LASTEXITCODE -ne 0) { throw "Test database failed to start" }
}

switch ($Suite) {
    "setup" {
        Write-Step "Installing test dependencies into backend\.venv"
        & $Python -m pip install -r (Join-Path $Testing "requirements-test.txt")
        & $Python -m playwright install chromium
        return
    }
    "db-down" { docker compose -f $Compose down; return }
    "unit"    { $paths = @("unit") }
    "api"     { Start-TestDb; $paths = @("api") }
    "e2e"     { Start-TestDb; $paths = @("e2e") }
    "all"     { Start-TestDb; $paths = @("unit", "api", "e2e") }
}

$report = Join-Path $Testing "reports\report.html"
Push-Location $Testing
try {
    Write-Step "Running: pytest $($paths -join ' ') $PytestArgs"
    & $Python -m pytest @paths --html=$report --self-contained-html @PytestArgs
    $code = $LASTEXITCODE
} finally { Pop-Location }

Write-Host ""
Write-Host "HTML report: $report" -ForegroundColor Green
Write-Host "XFAIL = known bug (see testing\docs\BUG_REPORTS.md). XPASS = a bug got fixed: close it." -ForegroundColor DarkGray
exit $code
