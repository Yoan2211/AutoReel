@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" "%~dp0autoreel_gui.py"
) else if exist ".venv\Scripts\python.exe" (
    start "" ".venv\Scripts\python.exe" "%~dp0autoreel_gui.py"
) else (
    py -3.11 "%~dp0autoreel_gui.py"
)
