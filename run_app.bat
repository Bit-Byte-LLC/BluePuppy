@echo off
REM Quick run script for BluePuppy

echo Starting BluePuppy...

REM Check if virtual environment exists
if not exist .venv (
    echo Virtual environment not found!
    echo Please run setup.bat first
    pause
    exit /b 1
)

REM Activate and run
call .venv\Scripts\activate.bat
python -m app.main

if %ERRORLEVEL% NEQ 0 (
    echo Application exited with error
    pause
)
