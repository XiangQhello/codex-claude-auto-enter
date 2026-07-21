$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    & (Join-Path $Root "scripts\install\windows.ps1")
}

& $Python -m pip install pyinstaller
Push-Location $Root
try {
    & $Python -m PyInstaller --noconfirm --clean --windowed --name "解放单手" --paths (Join-Path $Root "src") (Join-Path $Root "src\app.py")
} finally {
    Pop-Location
}
Write-Host "独立版已生成：$Root\dist\解放单手.exe"
