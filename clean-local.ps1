# Clean up local build artifacts
# Usage: .\clean-local.ps1

Write-Host "Cleaning local build artifacts..." -ForegroundColor Yellow

# Build output folders
Remove-Item -Recurse -Force dist, dist_helper -ErrorAction SilentlyContinue

# Downloaded/extracted NuGet packages
Remove-Item -Recurse -Force lhm, lhm_extract, hidsharp_extract -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force Microsoft.*_extract, System.*_extract -ErrorAction SilentlyContinue

# Downloaded NuGet zips (specific names only)
Remove-Item -Force lhm.zip, hidsharp.zip -ErrorAction SilentlyContinue
Remove-Item -Force Microsoft.*.zip, System.*.zip -ErrorAction SilentlyContinue

# Build output zips (ThermalEngine-*.zip is the portable build)
Remove-Item -Force ThermalEngine-*.zip, ThermalEngine-*-Setup.exe -ErrorAction SilentlyContinue

Write-Host "Done." -ForegroundColor Green
