$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

Write-Host "[1/3] Validating 194-work slate..." -ForegroundColor Cyan
python .\scripts\validate_catalog.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[2/3] Auditing exact and semantic duplicates..." -ForegroundColor Cyan
python .\scripts\audit_duplicates.py --check
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[3/3] Compiling prompts, manifests and offline site..." -ForegroundColor Cyan
python .\scripts\build_all.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`nBuild complete." -ForegroundColor Green
Write-Host "Open: $PSScriptRoot\generated\site\index.html"
Write-Host "Catalog: $PSScriptRoot\generated\catalog\ALL_194.md"
