# Clean up local build artifacts
# Usage: .\scripts\clean-local.ps1 (from project root)
#    or: .\clean-local.ps1 (from scripts folder)

# Change to project root (script can be run from scripts/ or project root)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
if (Test-Path "$ProjectRoot\main.py") {
    Set-Location $ProjectRoot
}

Write-Host "Cleaning local build artifacts..." -ForegroundColor Yellow

# Build output folders
Remove-Item -Recurse -Force dist -ErrorAction SilentlyContinue

# Build output zips and installers
Remove-Item -Force ThermalEngine-*.zip, ThermalEngine-*-Setup.exe -ErrorAction SilentlyContinue

Write-Host "Done." -ForegroundColor Green
