@echo off
chcp 65001 > nul
echo ====================================================
echo  Windows タスクスケジューラ登録 (毎朝 06:00 自動実行)
echo ====================================================
echo.
set TASK_NAME=TikTokCompareDaily6AM
set BAT_PATH=%~dp0run_daily_automation.bat

schtasks /create /tn "%TASK_NAME%" /tr "\"%BAT_PATH%\"" /sc daily /st 06:00 /f

if %ERRORLEVEL% equ 0 (
    echo.
    echo [成功] 毎朝 06:00 の自動実行タスクを正常に登録しました！
) else (
    echo.
    echo [失敗] 管理者権限が必要な場合があります。「管理者として実行」してください。
)
pause
