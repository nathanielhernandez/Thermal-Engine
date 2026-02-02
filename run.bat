@echo off
cd /d "%~dp0"

:: Check for virtual environment
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

:: Run the application
python main.py

:: Keep window open if there was an error
if errorlevel 1 pause
