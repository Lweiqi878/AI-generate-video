@echo off
setlocal
cd /d "%~dp0"

echo [1/2] Validating 100-work slate...
python scripts\validate_catalog.py
if errorlevel 1 goto :error

echo [2/2] Compiling prompts, manifests and offline site...
python scripts\build_all.py
if errorlevel 1 goto :error

echo.
echo Build complete.
echo Open: generated\site\index.html
echo Catalog: generated\catalog\ALL_100.md
pause
exit /b 0

:error
echo.
echo Build failed. Read the error above.
pause
exit /b 1
