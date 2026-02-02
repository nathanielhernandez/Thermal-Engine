@echo off
setlocal EnableDelayedExpansion

echo ============================================
echo   Thermal Engine - Installation Script
echo ============================================
echo.

:: Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.10 or later from https://www.python.org/
    pause
    exit /b 1
)

echo [OK] Python found
python --version
echo.

:: Check for pip
pip --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pip is not available. Please reinstall Python with pip included.
    pause
    exit /b 1
)

echo [OK] pip found
echo.

:: Ask about virtual environment
set /p VENV_CHOICE="Create a virtual environment? (recommended) [Y/n]: "
if /i "%VENV_CHOICE%"=="n" goto :skip_venv

echo.
echo Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo [WARNING] Failed to create virtual environment. Continuing with system Python...
    goto :skip_venv
)

echo Activating virtual environment...
call venv\Scripts\activate.bat
echo [OK] Virtual environment activated
echo.

:skip_venv

:: Install Python dependencies
echo Installing Python dependencies...
echo This may take a few minutes...
echo.
pip install -r requirements.txt
if errorlevel 1 (
    echo [WARNING] Some packages may have failed to install.
    echo The editor may still work with reduced functionality.
)
echo.

:: Check for SensorHelperApp
if exist "lhm\SensorHelperApp.exe" (
    echo [OK] SensorHelperApp found
) else (
    echo [WARNING] lhm\SensorHelperApp.exe not found.
    echo CPU/GPU sensor monitoring will not work.
    echo Please ensure the lhm folder is present with SensorHelperApp.exe
)
echo.

:: Create presets folder if it doesn't exist
if not exist "presets" mkdir presets

echo.
echo ============================================
echo   Installation Complete!
echo ============================================
echo.
echo To run the editor:
if exist "venv\Scripts\activate.bat" (
    echo   1. Open a command prompt in this folder
    echo   2. Run: venv\Scripts\activate
    echo   3. Run: python main.py
    echo.
    echo Or simply double-click 'run.bat'
) else (
    echo   Run: python main.py
)
echo.
echo IMPORTANT: Run as Administrator for full sensor support!
echo.
pause
