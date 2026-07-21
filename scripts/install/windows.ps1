$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Venv = Join-Path $Root ".venv"
$VenvPython = Join-Path $Venv "Scripts\python.exe"

Write-Host "[解放单手] 正在查找 Python 3……"
if (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonExe = (Get-Command py).Source
    $PythonArgs = @("-3")
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonExe = (Get-Command python).Source
    $PythonArgs = @()
} else {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Host "[解放单手] 没有找到 Python 3，正在通过 winget 安装……"
        winget install --exact --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
        $Candidate = Get-ChildItem "$env:LOCALAPPDATA\Programs\Python\Python*\python.exe" -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 1
        if ($null -eq $Candidate) {
            throw "Python 安装完成但当前脚本没有找到 python.exe，请重新运行一键启动.bat。"
        }
        $PythonExe = $Candidate.FullName
        $PythonArgs = @()
    } else {
        throw "没有找到 Python 3，也没有 winget。请从 python.org 安装 Python 3。"
    }
}

if (-not (Test-Path $VenvPython)) {
    Write-Host "[解放单手] 正在创建独立 Python 环境……"
    & $PythonExe @PythonArgs -m venv $Venv
}

& $VenvPython -c "import PyQt5" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[解放单手] 正在安装 Qt 界面依赖……"
    & $VenvPython -m pip install -r (Join-Path $Root "requirements.txt")
}

$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop "解放单手.lnk"
$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = Join-Path $Root "一键启动.bat"
$Shortcut.WorkingDirectory = $Root
$Shortcut.Description = "多终端并行自动回车控制台"
$Shortcut.Save()

Write-Host "[解放单手] 安装完成，桌面快捷方式：$ShortcutPath"
