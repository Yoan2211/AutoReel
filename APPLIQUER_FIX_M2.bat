@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" "%~dp0apply_m2_punctuation_fix.py"
) else (
    py -3.11 "%~dp0apply_m2_punctuation_fix.py"
)
