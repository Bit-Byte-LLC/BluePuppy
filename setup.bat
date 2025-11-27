@echo off
REM Setup script for BluePuppy
REM Checks prerequisites and installs dependencies

echo ========================================
echo BluePuppy - Setup Script
echo ========================================
echo.

REM Check Python installation
echo [1/4] Checking Python installation...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not found!
    echo Please install Python 3.11 or higher from https://www.python.org/
    pause
    exit /b 1
)

python --version
echo OK: Python is installed
echo.

REM Check Python version
python -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python 3.11+ required
    echo Please upgrade Python from https://www.python.org/
    pause
    exit /b 1
)

echo OK: Python version is 3.11+
echo.

REM Check if virtual environment exists
if exist .venv (
    echo [2/4] Virtual environment already exists
) else (
    echo [2/4] Creating virtual environment...
    python -m venv .venv
    if %ERRORLEVEL% NEQ 0 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo OK: Virtual environment created
)
echo.

REM Activate virtual environment and install dependencies
echo [3/4] Installing dependencies...
call .venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo OK: Dependencies installed
echo.

REM Verify installation
echo [4/4] Verifying installation...
python -c "import bleak, PySide6, qasync, cbor2, serial, structlog" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo WARNING: Some dependencies may not be properly installed
) else (
    echo OK: All dependencies verified
)
echo.

echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo To run the application:
echo   1. Activate virtual environment: .venv\Scripts\activate
echo   2. Run: python -m app.main
echo.
echo Or simply run: run_app.bat
echo.
echo To build executable: scripts\build_windows.bat
echo.
echo For help, see README.md or QUICKSTART.md
echo.

pause
