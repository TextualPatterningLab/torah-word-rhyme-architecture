@echo off
setlocal
python "%~dp0..\src\preprocess_corpus.py" %*
exit /b %errorlevel%
