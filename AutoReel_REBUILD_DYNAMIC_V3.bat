@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" "%~dp0autoreel_rebuild_dynamic_v3.py"
) else (
    py -3.11 "%~dp0autoreel_rebuild_dynamic_v3.py"
)
