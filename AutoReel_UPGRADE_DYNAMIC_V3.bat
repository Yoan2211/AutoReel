@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" "%~dp0upgrade_autoreel_dynamic_v3.py"
) else (
    py -3.11 "%~dp0upgrade_autoreel_dynamic_v3.py"
)
