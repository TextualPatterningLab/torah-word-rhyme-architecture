@echo off
setlocal
call "%~dp0inspect_passage.bat" --book deuteronomy --start 11:10 --end 11:15 --exact-words include --window-left 20 --label deuteronomy_11-10_11-15_strict
exit /b %errorlevel%
