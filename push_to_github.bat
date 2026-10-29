@echo off
chcp 65001 > nul
echo ====================================================
echo  GitHub へプロジェクトをアップロード (Push)
echo  リポジトリ: yuueki1116-ctrl/tiktok-compare-remotion
echo ====================================================
echo.
cd /d "%~dp0"

echo [1/3] リモートURLを設定中...
git remote set-url origin https://github.com/yuueki1116-ctrl/tiktok-compare-remotion.git
git branch -M main

echo [2/3] GitHub へ送信中...
echo ※ ブラウザまたは認証画面が開いた場合はログイン（認証）を許可してください。
echo.
git push -u origin main

if %ERRORLEVEL% equ 0 (
    echo.
    echo ====================================================
    echo [成功] GitHubへのアップロードが完了しました！
    echo 毎朝 06:00 の自動動画生成・Discord納品が稼働開始しました！
    echo ====================================================
) else (
    echo.
    echo ====================================================
    echo [認証エラーの場合]
    echo 既存の別アカウントでログインされている可能性があります。
    echo コマンドプロンプト等で認証するか、Personal Access Token をご利用ください。
    echo ====================================================
)
pause
