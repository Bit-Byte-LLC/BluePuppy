@echo off
REM Build script for BluePuppy on Windows
REM Runs tests, linting, and creates PyInstaller distributions

echo ========================================
echo BluePuppy - Windows Build Script
echo ========================================
echo.

REM Check if virtual environment exists
if not exist .venv (
    echo ERROR: Virtual environment not found!
    echo Please run setup.bat first to create .venv
    pause
    exit /b 1
)

REM Use virtual environment Python directly
set PYTHON_EXE=.venv\Scripts\python.exe

REM Check Python version
%PYTHON_EXE% --version
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not found in PATH
    exit /b 1
)

echo.
echo [1/5] Installing dependencies...
%PYTHON_EXE% -m pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install dependencies
    exit /b 1
)

echo.
echo [2/5] Running code formatters...
%PYTHON_EXE% -m black app tests --check
if %ERRORLEVEL% NEQ 0 (
    echo WARNING: Code formatting issues found
    echo Run: %PYTHON_EXE% -m black app tests
)

echo.
echo [3/5] Running linter...
%PYTHON_EXE% -m ruff check app tests
if %ERRORLEVEL% NEQ 0 (
    echo WARNING: Linting issues found
)

echo.
echo [4/5] Running tests...
%PYTHON_EXE% -m pytest tests -v
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Tests failed
    exit /b 1
)

echo.
echo [5/5] Building with PyInstaller...

REM Clean previous builds
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

# Build using spec file
%PYTHON_EXE% -m PyInstaller app_build\BluePuppy.spec
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: PyInstaller build failed
    exit /b 1
)

echo.
echo ========================================
echo Build Complete!
echo ========================================
echo.
echo One-folder build: dist\BluePuppy\
echo One-file build: dist\BluePuppy-Portable.exe
echo.
echo To run the app:
echo   dist\BluePuppy\BluePuppy.exe
echo   or
echo   dist\BluePuppy-Portable.exe
echo.

pause
