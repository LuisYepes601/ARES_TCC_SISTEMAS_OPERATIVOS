@echo off
title Ares v3.0 - System Monitor
echo.
echo   Ares v3.0 - System Monitor
echo.

python --version >nul 2>&1
if errorlevel 1 ( echo ERROR: Python not found. Install from https://python.org & pause & exit /b )

if not exist "venv" python -m venv venv
call venv\Scripts\activate.bat
pip install -q -r requirements.txt

echo Starting Ares...
python main.py
pause
