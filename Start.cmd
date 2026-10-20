@echo off
cd /d "%~dp0"
python app.py desktop
if errorlevel 1 pause
