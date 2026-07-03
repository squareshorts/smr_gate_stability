@echo off
setlocal
cd /d "%~dp0"
python analysis_replication\run_full_replication.py
python analysis_replication\finish_replication.py
endlocal
