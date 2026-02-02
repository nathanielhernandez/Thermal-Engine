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

:: Check for SensorHelperApp
if not exist "lhm\SensorHelperApp.exe" (
    echo [WARNING] lhm\SensorHelperApp.exe not found.
    echo Sensor monitoring will not work in the built executable.
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
    --add-data "lhm;lhm" ^
    --hidden-import "PySide6.QtSvg" ^
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
