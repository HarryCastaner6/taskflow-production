@echo off
echo ========================================
echo TaskFlow - Quick Deployment Script
echo ========================================

echo.
echo 1. Checking git status...
git status

echo.
echo 2. Adding all changes...
git add .

echo.
echo 3. Committing changes...
set /p commit_msg="Enter commit message (or press Enter for auto-message): "
if "%commit_msg%"=="" (
    git commit -m "🚀 TaskFlow update - auto-deploy"
) else (
    git commit -m "%commit_msg%"
)

echo.
echo 4. Pushing to GitHub...
git push origin main

echo.
echo 5. Deploying to Vercel...
vercel --prod

echo.
echo ========================================
echo Deployment Complete!
echo ========================================
echo.
echo Your live site will be available at:
echo https://taskflow-production.vercel.app
echo.
echo Press any key to exit...
pause >nul