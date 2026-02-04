# Local Build Script - Mirrors GitHub Actions workflow exactly
# This script should NOT be committed to the repository
# Usage: .\build-local.ps1

param(
    [string]$Version = "local-dev",
    [switch]$SkipInstaller,
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$BuildDir = "dist"
$HelperDir = "dist_helper"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ThermalEngine Local Build" -ForegroundColor Cyan
Write-Host "  Version: $Version" -ForegroundColor Cyan
Write-Host "  Branch: $(git branch --show-current)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Clean previous build if requested
if ($Clean) {
    Write-Host "`n[1/8] Cleaning previous build..." -ForegroundColor Yellow
    if (Test-Path $BuildDir) { Remove-Item -Recurse -Force $BuildDir }
    if (Test-Path $HelperDir) { Remove-Item -Recurse -Force $HelperDir }
    if (Test-Path "lhm") { Remove-Item -Recurse -Force "lhm" }
    if (Test-Path "lhm_extract") { Remove-Item -Recurse -Force "lhm_extract" }
    if (Test-Path "hidsharp_extract") { Remove-Item -Recurse -Force "hidsharp_extract" }
    Get-ChildItem -Filter "*_extract" -Directory | Remove-Item -Recurse -Force
    Get-ChildItem -Filter "*.nupkg" | Remove-Item -Force
} else {
    Write-Host "`n[1/8] Skipping clean (use -Clean to remove previous build)" -ForegroundColor Gray
}

# Install Python dependencies
Write-Host "`n[2/8] Installing Python dependencies..." -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
pip install nuitka ordered-set zstandard --quiet

# Download LibreHardwareMonitor DLLs
Write-Host "`n[3/8] Downloading LibreHardwareMonitor DLLs..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "lhm" | Out-Null

# Download and extract LibreHardwareMonitor NuGet package
if (-not (Test-Path "lhm/LibreHardwareMonitorLib.dll")) {
    Invoke-WebRequest -Uri "https://www.nuget.org/api/v2/package/LibreHardwareMonitorLib/0.9.3" -OutFile "lhm.zip"
    Expand-Archive -Path "lhm.zip" -DestinationPath "lhm_extract" -Force

    # Find and copy LibreHardwareMonitorLib.dll
    $lhmDll = Get-ChildItem -Path "lhm_extract" -Filter "LibreHardwareMonitorLib.dll" -Recurse | Select-Object -First 1
    if ($lhmDll) {
        Copy-Item $lhmDll.FullName -Destination "lhm/" -Force
        Copy-Item $lhmDll.FullName -Destination "." -Force
        Write-Host "  Copied LibreHardwareMonitorLib.dll"
    }

    # Find and copy HidSharp.dll
    $hidDll = Get-ChildItem -Path "lhm_extract" -Filter "HidSharp.dll" -Recurse | Select-Object -First 1
    if ($hidDll) {
        Copy-Item $hidDll.FullName -Destination "lhm/" -Force
        Copy-Item $hidDll.FullName -Destination "." -Force
        Write-Host "  Copied HidSharp.dll"
    } else {
        Write-Host "  HidSharp not in LHM package, downloading separately..."
        Invoke-WebRequest -Uri "https://www.nuget.org/api/v2/package/HidSharp/2.1.0" -OutFile "hidsharp.zip"
        Expand-Archive -Path "hidsharp.zip" -DestinationPath "hidsharp_extract" -Force
        $hidDll = Get-ChildItem -Path "hidsharp_extract" -Filter "HidSharp.dll" -Recurse | Select-Object -First 1
        if ($hidDll) {
            Copy-Item $hidDll.FullName -Destination "lhm/" -Force
            Copy-Item $hidDll.FullName -Destination "." -Force
            Write-Host "  Copied HidSharp.dll"
        } else {
            Write-Host "ERROR: Could not find HidSharp.dll" -ForegroundColor Red
            exit 1
        }
    }

    # Download additional .NET runtime DLLs
    $dlls = @(
        @{name="Microsoft.Win32.Registry"; version="5.0.0"},
        @{name="System.Security.AccessControl"; version="6.0.0"},
        @{name="System.Security.Principal.Windows"; version="5.0.0"},
        @{name="System.IO.FileSystem.AccessControl"; version="5.0.0"}
    )

    foreach ($dll in $dlls) {
        $url = "https://www.nuget.org/api/v2/package/$($dll.name)/$($dll.version)"
        $outFile = "$($dll.name).zip"
        Invoke-WebRequest -Uri $url -OutFile $outFile
        Expand-Archive -Path $outFile -DestinationPath "$($dll.name)_extract" -Force

        $dllFile = Get-ChildItem -Path "$($dll.name)_extract" -Filter "*.dll" -Recurse | Where-Object { $_.Name -like "$($dll.name).dll" } | Select-Object -First 1
        if ($dllFile) {
            Copy-Item $dllFile.FullName -Destination "." -Force
            Write-Host "  Copied $($dllFile.Name)"
        }
    }
} else {
    Write-Host "  DLLs already downloaded, skipping..."
}

# Build SensorHelperApp
Write-Host "`n[4/8] Building SensorHelperApp..." -ForegroundColor Yellow
Push-Location SensorHelperApp
dotnet restore --verbosity quiet
dotnet publish -c Release -o ../dist_helper --verbosity quiet
Pop-Location

if (Test-Path "dist_helper/SensorHelperApp.exe") {
    Copy-Item "dist_helper/SensorHelperApp.exe" "." -Force
    Write-Host "  SensorHelperApp built successfully"
} else {
    Write-Host "ERROR: SensorHelperApp.exe not found" -ForegroundColor Red
    exit 1
}

# Build with Nuitka
Write-Host "`n[5/8] Building with Nuitka (this may take several minutes)..." -ForegroundColor Yellow
python -m nuitka `
    --standalone `
    --windows-console-mode=disable `
    --windows-icon-from-ico=assets/icon.ico `
    --windows-uac-admin `
    --enable-plugin=pyside6 `
    --include-package=cv2 `
    --include-package=numpy `
    --include-package=PIL `
    --include-package=psutil `
    --include-package=hid `
    --include-package=elements `
    --include-data-dir=presets=presets `
    --include-data-files=elements/*.py=elements/ `
    --include-data-files=assets/icon.ico=icon.ico `
    --include-data-files=assets/icon.png=icon.png `
    --assume-yes-for-downloads `
    --output-dir=dist `
    --output-filename=ThermalEngine.exe `
    main.py

# Verify build output
if (-not (Test-Path "dist\main.dist\elements")) {
    Write-Host "ERROR: elements folder missing!" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path "dist\main.dist\presets")) {
    Write-Host "ERROR: presets folder missing!" -ForegroundColor Red
    exit 1
}

# Rename output folder
if (Test-Path "dist\main.dist") {
    if (Test-Path "dist\ThermalEngine") {
        Remove-Item -Recurse -Force "dist\ThermalEngine"
    }
    Move-Item -Path "dist\main.dist" -Destination "dist\ThermalEngine" -Force
}
Write-Host "  Nuitka build complete"

# Copy SensorHelper to dist
Write-Host "`n[6/8] Copying SensorHelper to distribution..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "dist/ThermalEngine/SensorHelper" | Out-Null
Copy-Item "dist_helper/*" "dist/ThermalEngine/SensorHelper/" -Recurse -Force

# Copy native driver files
$nugetCache = "$env:USERPROFILE\.nuget\packages\librehardwaremonitorlib"
$nativeFiles = Get-ChildItem -Path $nugetCache -Recurse -Include "*.sys","*.dll" -ErrorAction SilentlyContinue |
               Where-Object { $_.FullName -like "*runtimes*" -or $_.FullName -like "*native*" }

foreach ($file in $nativeFiles) {
    Copy-Item $file.FullName -Destination "dist/ThermalEngine/SensorHelper/" -Force
}

$lhmNative = Get-ChildItem -Path "lhm_extract" -Recurse -Include "*.sys" -ErrorAction SilentlyContinue
foreach ($file in $lhmNative) {
    Copy-Item $file.FullName -Destination "dist/ThermalEngine/SensorHelper/" -Force
}

# Verify critical files
if (-not (Test-Path "dist/ThermalEngine/SensorHelper/LibreHardwareMonitorLib.dll")) {
    Write-Host "ERROR: LibreHardwareMonitorLib.dll not found!" -ForegroundColor Red
    exit 1
}
Write-Host "  SensorHelper copied successfully"

# Create ZIP archive
Write-Host "`n[7/8] Creating ZIP archive..." -ForegroundColor Yellow
$zipName = "ThermalEngine-$Version.zip"
if (Test-Path $zipName) { Remove-Item $zipName }
Compress-Archive -Path "dist/ThermalEngine/*" -DestinationPath $zipName
Write-Host "  Created $zipName"

# Build installer (optional)
if (-not $SkipInstaller) {
    Write-Host "`n[8/8] Building installer with Inno Setup..." -ForegroundColor Yellow
    $innoPath = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    if (Test-Path $innoPath) {
        & $innoPath "/DMyAppVersion=$Version" "installer.iss"
        Write-Host "  Installer built successfully"
    } else {
        Write-Host "  Inno Setup not found, skipping installer (install with: choco install innosetup)" -ForegroundColor Gray
    }
} else {
    Write-Host "`n[8/8] Skipping installer (use without -SkipInstaller to build)" -ForegroundColor Gray
}

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  Build Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "Output: dist\ThermalEngine\" -ForegroundColor White
Write-Host "ZIP:    $zipName" -ForegroundColor White
Write-Host "Run:    dist\ThermalEngine\ThermalEngine.exe" -ForegroundColor White
Write-Host ""
