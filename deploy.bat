@echo off
chcp 65001
echo ==========================================
echo      Segawa Lab Auto Deploy System
echo ==========================================

echo.
echo [1/3] Converting articles to JSON...
python txt2json.py posts

echo.
echo [2/3] Staging files for Git...
git add .

echo.
echo [3/3] Committing and Pushing to GitHub...
set /p commit_msg="Enter commit message (default: update): "
if "%commit_msg%"=="" set commit_msg=update

git commit -m "%commit_msg%"
git push origin main

echo.
echo ==========================================
echo             Done!
echo ==========================================
pause
