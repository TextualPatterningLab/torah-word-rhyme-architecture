@echo off
setlocal

set SCRIPT_DIR=%~dp0
set REPO_ROOT=%SCRIPT_DIR%..

if "%~1"=="" (
    python "%REPO_ROOT%\src\visualize_distribution.py" --label default_strict
) else (
    python "%REPO_ROOT%\src\visualize_distribution.py" %*
)

endlocal