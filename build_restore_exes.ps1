# ER-ServiceDesk/build_restore_exes.ps1
#
# Builds the two standalone database restore tools. Run from the
# project root, on a real Windows machine, WITH THE PROJECT'S VENV
# ACTIVATED FIRST:
#
#     .\venv\Scripts\Activate.ps1
#     .\build_restore_exes.ps1
#
# Unlike build_exe.ps1 (the main desktop app), these two tools use
# only the Python standard library -- no PySide6, nothing else to
# verify is importable beyond PyInstaller itself.
#
# Output: dist\RestoreDatabaseLocal.exe and dist\RestoreDatabaseServer.exe
# (onefile builds -- see either .spec file's own header for why
# onefile is the right choice for these two specifically, unlike the
# main app's onedir build).

$ErrorActionPreference = "Stop"

function Test-LastCommand {
    param([string]$StepName)
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "ERROR: '$StepName' failed (exit code $LASTEXITCODE). See the output above for the real reason." -ForegroundColor Red
        exit 1
    }
}

Write-Host "Verifying PyInstaller is actually importable in this environment..." -ForegroundColor Cyan
python -c "import PyInstaller"
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: PyInstaller is not importable in this Python environment." -ForegroundColor Red
    Write-Host "This almost always means the project's venv isn't activated." -ForegroundColor Red
    Write-Host "Run this first, then try again:" -ForegroundColor Yellow
    Write-Host "    .\venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    exit 1
}

Write-Host "Building RestoreDatabaseLocal.exe..." -ForegroundColor Cyan
python -m PyInstaller installer/RestoreDatabaseLocal.spec
Test-LastCommand "PyInstaller build (Local)"

Write-Host "Building RestoreDatabaseServer.exe..." -ForegroundColor Cyan
python -m PyInstaller installer/RestoreDatabaseServer.spec
Test-LastCommand "PyInstaller build (Server)"

Write-Host ""
Write-Host "Build complete:" -ForegroundColor Green
Write-Host "    dist\RestoreDatabaseLocal.exe" -ForegroundColor Green
Write-Host "    dist\RestoreDatabaseServer.exe" -ForegroundColor Green
