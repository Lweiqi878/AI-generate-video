$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

Write-Host "[1/5] Validating 194-work slate..." -ForegroundColor Cyan
python .\scripts\validate_catalog.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[2/5] Auditing exact and semantic duplicates..." -ForegroundColor Cyan
python .\scripts\audit_duplicates.py --check
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[3/5] Compiling prompts, manifests and offline site..." -ForegroundColor Cyan
python .\scripts\build_all.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[4/5] Building posting cards and upload queue..." -ForegroundColor Cyan
python .\scripts\build_publishing.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[5/5] Validating publish-ready releases..." -ForegroundColor Cyan
python .\scripts\validate_releases.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`nBuild complete." -ForegroundColor Green
Write-Host "Open: $PSScriptRoot\generated\site\index.html"
Write-Host "Catalog: $PSScriptRoot\generated\catalog\ALL_194.md"
Write-Host "Publishing: $PSScriptRoot\publishing\README.md"
