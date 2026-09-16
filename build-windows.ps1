$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    Write-Host "Python for Windows was not found. Install Python 3.10+ with the Python launcher." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path ".venv")) { py -3 -m venv .venv }
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
& $python -m pip install --upgrade pip pyinstaller

$iconArgs = @()
if (Test-Path "assets\icon.ico") { $iconArgs = @("--icon", "assets\icon.ico") }
& $python -m PyInstaller --noconfirm --clean --onefile --windowed @iconArgs --name "Needle" "needle_desktop.pyw"

if (-not (Test-Path "dist\Needle.exe")) { throw "Build did not create dist\Needle.exe" }
Write-Host "Built: $PSScriptRoot\dist\Needle.exe" -ForegroundColor Green
