@echo off
chcp 65001 > nul
echo ====================================================
echo  Daily Compare Video Automation (Render + Discord)
echo ====================================================
cd /d "%~dp0"
python daily_automation.py
pause
