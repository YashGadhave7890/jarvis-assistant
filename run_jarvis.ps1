<#
.SYNOPSIS
    JARVIS AI Assistant — Production PowerShell Launcher
.DESCRIPTION
    Automates environment verification, venv activation, dependency checks,
    and launches the Jarvis Quantum Intelligence HUD.
#>

[CmdletBinding()]
param(
    [string]$Mode = "hud",
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8000,
    [switch]$NoBrowser,
    [switch]$Silent,
    [switch]$VerboseLog
)

$Host.UI.RawUI.WindowTitle = "JARVIS AI Assistant — Quantum HUD"

Write-Host "===================================================================" -ForegroundColor Cyan
Write-Host "               JARVIS AI ASSISTANT — POWERSHELL LAUNCHER          " -ForegroundColor White
Write-Host "         Quantum Live HUD • Continuous Voice • Dual Input         " -ForegroundColor DarkCyan
Write-Host "===================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check Python
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "[ERROR] Python 3.10+ was not found in PATH." -ForegroundColor Red
    Write-Host "Please install Python from https://www.python.org/downloads/ and check 'Add to PATH'." -ForegroundColor Yellow
    pause
    exit 1
}

# 2. Check .env template
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Write-Host "[INFO] Creating .env from .env.example template..." -ForegroundColor Yellow
        Copy-Item ".env.example" ".env"
        Write-Host "[INFO] Created .env. Please configure your GROQ_API_KEY." -ForegroundColor Green
    }
}

# 3. Verify Virtual Environment
$venvActivate = "venv\Scripts\Activate.ps1"
if (-not (Test-Path $venvActivate)) {
    Write-Host "[SETUP] Creating virtual environment (venv)..." -ForegroundColor Yellow
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to create virtual environment." -ForegroundColor Red
        pause
        exit 1
    }
}

# 4. Activate Venv
Write-Host "[SETUP] Activating virtual environment..." -ForegroundColor Green
& $venvActivate

# 5. Check dependencies
Write-Host "[SETUP] Verifying core dependencies..." -ForegroundColor Gray
python -c "import fastapi, uvicorn, groq, edge_tts, faster_whisper" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[SETUP] Installing required packages from requirements.txt..." -ForegroundColor Yellow
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Dependency installation failed." -ForegroundColor Red
        pause
        exit 1
    }
}

# 6. Check if port is in use
$portInUse = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
if ($portInUse) {
    Write-Host "[WARN] Port $Port is currently occupied by PID $($portInUse[0].OwningProcess)." -ForegroundColor Yellow
    Write-Host "Jarvis will attempt to bind or you can specify -Port <new_port>." -ForegroundColor Gray
}

# 7. Launch Jarvis
Write-Host "[START] Launching Jarvis in $Mode mode..." -ForegroundColor Cyan
Write-Host "[INFO] Quantum HUD available at http://${HostAddress}:${Port}" -ForegroundColor Green
Write-Host ""

$argsList = @("main.py", "--mode", $Mode, "--host", $HostAddress, "--port", $Port)
if ($NoBrowser) { $argsList += "--no-browser" }
if ($Silent) { $argsList += "--silent" }
if ($VerboseLog) { $argsList += "--verbose" }

python @argsList
