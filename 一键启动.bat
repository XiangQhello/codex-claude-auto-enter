@echo off
chcp 65001 >nul
set "ROOT=%~dp0"
set "PYTHON_LAUNCHER="

if defined HANDSFREE_PYTHON call :try_python "%HANDSFREE_PYTHON%"
if not defined PYTHON_LAUNCHER if defined CONDA_PREFIX call :try_python "%CONDA_PREFIX%\python.exe"
if not defined PYTHON_LAUNCHER call :try_python "%ROOT%.venv\Scripts\python.exe"

if not defined PYTHON_LAUNCHER (
    call "%ROOT%scripts\install\windows.bat"
    if errorlevel 1 exit /b %errorlevel%
    call :try_python "%ROOT%.venv\Scripts\python.exe"
)

if not defined PYTHON_LAUNCHER (
    echo [解放单手] 没有找到可用的 Python 环境。
    pause
    exit /b 1
)

start "解放单手" "%PYTHON_LAUNCHER%" "%ROOT%src\app.py"
exit /b 0

:try_python
set "CANDIDATE=%~1"
if not exist "%CANDIDATE%" exit /b 0
"%CANDIDATE%" -c "import PyQt5" >nul 2>&1
if errorlevel 1 exit /b 0
set "PYTHON_LAUNCHER=%CANDIDATE%"
for %%F in ("%CANDIDATE%") do set "PYTHONW_CANDIDATE=%%~dpFpythonw.exe"
if exist "%PYTHONW_CANDIDATE%" set "PYTHON_LAUNCHER=%PYTHONW_CANDIDATE%"
exit /b 0
