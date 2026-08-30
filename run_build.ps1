$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

Write-Host "[1/2] Validating 100-work slate..." -ForegroundColor Cyan
python .\scripts\validate_catalog.py

Write-Host "[2/2] Compiling prompts, manifests and offline site..." -ForegroundColor Cyan
python .\scripts\build_all.py

Write-Host "`nBuild complete." -ForegroundColor Green
Write-Host "Open: $PSScriptRoot\generated\site\index.html"
Write-Host "Catalog: $PSScriptRoot\generated\catalog\ALL_100.md"
