@echo off
setlocal
cd /d "%~dp0"

echo [1/5] Validating 194-work slate...
python scripts\validate_catalog.py
if errorlevel 1 goto :error

echo [2/5] Auditing exact and semantic duplicates...
python scripts\audit_duplicates.py --check
if errorlevel 1 goto :error

echo [3/5] Compiling prompts, manifests and offline site...
python scripts\build_all.py
if errorlevel 1 goto :error

echo [4/5] Building posting cards and upload queue...
python scripts\build_publishing.py
if errorlevel 1 goto :error

echo [5/5] Validating publish-ready releases...
python scripts\validate_releases.py
if errorlevel 1 goto :error

echo.
echo Build complete.
echo Open: generated\site\index.html
echo Catalog: generated\catalog\ALL_194.md
echo Publishing: publishing\README.md
pause
exit /b 0

:error
echo.
echo Build failed. Read the error above.
pause
exit /b 1
