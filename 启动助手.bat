@echo off
chcp 65001 > nul
call conda activate terraria-sync
python "%~dp0main.py"
if errorlevel 1 pause
