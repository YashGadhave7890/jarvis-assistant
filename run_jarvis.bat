@echo off
title JARVIS AI Assistant — Quantum HUD Launcher
color 0B

echo ===================================================================
echo               JARVIS AI ASSISTANT — 1-CLICK LAUNCHER              
echo         Quantum Live HUD • Continuous Voice • Dual Input         
echo ===================================================================
echo.

:: 1. Verify Python installation
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    color 0C
    echo [ERROR] Python is not installed or not found in system PATH.
    echo Please install Python 3.10 or 3.11 from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

:: 2. Check and copy .env if missing
if not exist ".env" (
    if exist ".env.example" (
        echo [INFO] No .env file found. Creating from .env.example template...
        copy ".env.example" ".env" >nul
        echo [INFO] Created .env. Please configure your GROQ_API_KEY in .env.
        echo.
    )
)

:: 3. Setup Virtual Environment if missing
if not exist "venv\Scripts\activate.bat" (
    echo [SETUP] Creating Python virtual environment (venv)...
    python -m venv venv
    if %ERRORLEVEL% neq 0 (
        color 0C
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [SETUP] Virtual environment created successfully.
    echo.
)

:: 4. Activate virtual environment
call venv\Scripts\activate.bat

:: 5. Install or verify dependencies
echo [SETUP] Verifying dependencies...
python -c "import fastapi, uvicorn, groq, edge_tts, faster_whisper" >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [SETUP] Installing required packages from requirements.txt...
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    if %ERRORLEVEL% neq 0 (
        color 0C
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
    echo [SETUP] Dependencies verified.
    echo.
)

:: 6. Launch Jarvis in Web HUD mode
echo [START] Launching Jarvis Quantum Intelligence HUD...
echo [INFO] Access HUD at: http://127.0.0.1:8000
echo.
python main.py --mode hud --port 8000

if %ERRORLEVEL% neq 0 (
    color 0C
    echo.
    echo [EXIT] Jarvis stopped with error code %ERRORLEVEL%.
    pause
)
