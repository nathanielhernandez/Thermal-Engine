@echo off
setlocal EnableDelayedExpansion

echo ============================================
echo   Thermal Engine - Build Executable
echo ============================================
echo.

:: Check for PyInstaller
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

:: Download DLLs if not present
if not exist "LibreHardwareMonitorLib.dll" (
    echo Downloading required DLLs...
    python download_lhm.py
)

:: Clean previous builds
echo Cleaning previous builds...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul

:: Build executable
echo.
echo Building executable...
echo.

pyinstaller ^
    --name "ThermalEngine" ^
    --onedir ^
    --windowed ^
    --icon "icon.ico" ^
    --add-data "presets;presets" ^
    --add-data "elements;elements" ^
    --add-data "LibreHardwareMonitorLib.dll;." ^
    --add-data "HidSharp.dll;." ^
    --add-data "Microsoft.Win32.Registry.dll;." ^
    --add-data "System.IO.FileSystem.AccessControl.dll;." ^
    --add-data "System.Security.AccessControl.dll;." ^
    --add-data "System.Security.Principal.Windows.dll;." ^
    --hidden-import "clr_loader" ^
    --hidden-import "pythonnet" ^
    --hidden-import "clr" ^
    --hidden-import "PySide6.QtSvg" ^
    --collect-all "clr_loader" ^
    main.py

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Build Complete!
echo ============================================
echo.
echo Executable location: dist\ThermalEngine\ThermalEngine.exe
echo.
echo To distribute, zip the entire dist\ThermalEngine folder.
echo.
pause
