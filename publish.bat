@echo off
set GH="C:\Program Files\GitHub CLI\gh.exe"
cd "C:\Users\PC\OneDrive\Documents\PythonProject\gestion-locative"

set /p VERSION="Version: "
if "%VERSION%"=="" exit /b 1

powershell -Command "(Get-Content 'electron-app\package.json') -replace '\"version\": \"[0-9.]+\"', '\"version\": \"%VERSION%\"' | Set-Content 'electron-app\package.json'"
powershell -Command "(Get-Content 'launcher.py') -replace 'VERSION = \"[0-9.]+\"', 'VERSION = \"%VERSION%\"' | Set-Content 'launcher.py'"
powershell -Command "(Get-Content 'installer.nsi') -replace '!define APP_VERSION \"[0-9.]+\"', '!define APP_VERSION \"%VERSION%\"' | Set-Content 'installer.nsi'"

call build.bat

git add -A
git commit -m "v%VERSION%"
git push origin main
git tag -a "v%VERSION%" -m "v%VERSION%"
git push origin "v%VERSION%"

%GH% release create "v%VERSION%" "Bay Bay Setup %VERSION%.exe" --title "v%VERSION%" --notes "v%VERSION%"

echo RELEASE OK: https://github.com/mlk0622/BayBay/releases/tag/v%VERSION%
pause