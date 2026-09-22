@echo off
setlocal
python "%~dp0..\src\download_sources.py" %*
exit /b %errorlevel%
