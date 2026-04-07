@echo off
set GH="C:\Program Files\GitHub CLI\gh.exe"
cd "C:\Users\PC\OneDrive\Documents\PythonProject\gestion-locative"

set /p VERSION="Version: "
if "%VERSION%"=="" exit /b 1

echo [1/5] Update versions
powershell -Command "(Get-Content 'electron-app\package.json') -replace '\"version\": \"[0-9.]+\"', '\"version\": \"%VERSION%\"' | Set-Content 'electron-app\package.json'"
powershell -Command "(Get-Content 'launcher.py') -replace 'VERSION = \"[0-9.]+\"', 'VERSION = \"%VERSION%\"' | Set-Content 'launcher.py'"
powershell -Command "(Get-Content 'installer.nsi') -replace '!define APP_VERSION \"[0-9.]+\"', '!define APP_VERSION \"%VERSION%\"' | Set-Content 'installer.nsi'"

echo [2/5] Build app
call build.bat

:: Revenir à la racine du projet au cas où build.bat a changé le répertoire
cd "C:\Users\PC\OneDrive\Documents\PythonProject\gestion-locative"

:: Chercher le setup dans les deux emplacements possibles
set SETUP_FILE=
if exist "Bay Bay Setup %VERSION%.exe" set SETUP_FILE=Bay Bay Setup %VERSION%.exe
if exist "electron-app\release\Bay Bay Setup %VERSION%.exe" set SETUP_FILE=electron-app\release\Bay Bay Setup %VERSION%.exe

if "%SETUP_FILE%"=="" (
    echo ERREUR: Setup non genere
    echo Fichiers present dans le dossier courant:
    dir *.exe 2>nul
    echo Fichiers present dans electron-app\release:
    dir electron-app\release\*.exe 2>nul
    pause
    exit /b 1
)

echo Setup trouve: %SETUP_FILE%

echo [3/5] Git commit
git add .gitignore electron-app\package.json launcher.py installer.nsi
git commit -m "v%VERSION%"
git push origin main

echo [4/5] Git tag
git tag -a "v%VERSION%" -m "v%VERSION%"
git push origin "v%VERSION%"

echo [5/5] GitHub release
%GH% release create "v%VERSION%" "%SETUP_FILE%" --title "v%VERSION%" --notes "v%VERSION%"

echo RELEASE OK: https://github.com/mlk0622/BayBay/releases/tag/v%VERSION%
pause