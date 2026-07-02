@echo off
setlocal
cd /d "%~dp0"
python tests\test_smoke.py
python utils\manifest.py
endlocal

