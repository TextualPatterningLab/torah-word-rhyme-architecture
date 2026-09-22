@echo off
setlocal
python "%~dp0..\src\inspect_passage.py" %*
exit /b %errorlevel%
