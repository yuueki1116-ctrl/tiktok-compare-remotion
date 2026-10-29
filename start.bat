@echo off
chcp 65001 > nul
echo ====================================================
echo  TikTok 4-way Compare Video Studio (Remotion)
echo ====================================================
echo.
cd /d "%~dp0"
set NODE_TLS_REJECT_UNAUTHORIZED=0
echo Starting server at http://localhost:3000 ...
start "" "http://localhost:3000"
node server.js
pause
