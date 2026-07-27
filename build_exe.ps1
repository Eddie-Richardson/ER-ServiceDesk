# ER-ServiceDesk/build_exe.ps1
#
# Builds the standalone desktop .exe. Run from the project root, on a
# real Windows machine, WITH THE PROJECT'S VENV ACTIVATED FIRST:
#
#     .\venv\Scripts\Activate.ps1
#     .\build_exe.ps1
#
# Every step below runs as `python -m ...` rather than calling pip /
# PyInstaller as bare commands -- bare commands resolve through PATH,
# which can silently pick up a different Python installation than the
# one that's actually active, even with the venv activated.
#
# $ErrorActionPreference = "Stop" only covers PowerShell's own cmdlet
# errors -- it does NOT stop the script if an external command (pip,
# python) exits with a failure code. Every external command below is
# followed by an explicit $LASTEXITCODE check for that reason, so a
# failed install step is caught and reported immediately, rather than
# silently continuing to a later, more confusing failure.
#
# Output: dist\ER-ServiceDesk\ER-ServiceDesk.exe (plus its supporting
# files in that same folder -- this is what the Inno Setup installer packages).

$ErrorActionPreference = "Stop"

function Test-LastCommand {
    param([string]$StepName)
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "ERROR: '$StepName' failed (exit code $LASTEXITCODE). See the output above for the real reason." -ForegroundColor Red
        exit 1
    }
}

Write-Host "Installing desktop build dependencies..." -ForegroundColor Cyan
python -m pip install -r desktop/requirements.txt
Test-LastCommand "pip install"

Write-Host "Verifying PySide6 is actually importable in this environment..." -ForegroundColor Cyan
python -c "import PySide6"
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: PySide6 is not importable in this Python environment." -ForegroundColor Red
    Write-Host "This almost always means the project's venv isn't activated." -ForegroundColor Red
    Write-Host "Run this first, then try again:" -ForegroundColor Yellow
    Write-Host "    .\venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    exit 1
}

Write-Host "Verifying PyInstaller is actually importable in this environment..." -ForegroundColor Cyan
python -c "import PyInstaller"
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: PyInstaller is not importable, even though pip install reported success." -ForegroundColor Red
    Write-Host "Check the pip install output above for what actually happened." -ForegroundColor Red
    exit 1
}

Write-Host "Building ER-ServiceDesk.exe..." -ForegroundColor Cyan
python -m PyInstaller ER-ServiceDesk.spec
Test-LastCommand "PyInstaller build"

Write-Host ""
Write-Host "Build complete: dist\ER-ServiceDesk\ER-ServiceDesk.exe" -ForegroundColor Green
