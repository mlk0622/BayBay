@echo off
setlocal enabledelayedexpansion

set "GH=C:\Program Files\GitHub CLI\gh.exe"
cd /d "%~dp0"

if not "%~1"=="" (
    set "VERSION=%~1"
) else (
    set /p VERSION="Version: "
)
if "%VERSION%"=="" exit /b 1

echo.
echo ========================================
echo   Bay Bay - Publication v%VERSION%
echo ========================================

echo [1/7] Update versions
py sync_version.py "%VERSION%"
if errorlevel 1 (
    echo ERREUR: sync_version.py a echoue
    pause
    exit /b 1
)

echo [2/7] Build app
call build.bat
if errorlevel 1 (
    echo ERREUR: Build a echoue
    pause
    exit /b 1
)

cd /d "%~dp0"

echo [3/7] Recherche du setup genere
set "SETUP_FILE="

if exist "Bay.Bay.Setup.%VERSION%.exe" (
    set "SETUP_FILE=Bay.Bay.Setup.%VERSION%.exe"
) else (
    for /f "delims=" %%F in ('dir /b /a:-d "Bay.Bay.Setup.%VERSION%*.exe" "Bay Bay Setup %VERSION%*.exe" "electron-app\release\Bay.Bay.Setup.%VERSION%*.exe" "electron-app\release\Bay Bay Setup %VERSION%*.exe" 2^>nul') do (
        set "SETUP_FILE=%%F"
        goto :setup_found
    )
)

:setup_found
if "%SETUP_FILE%"=="" (
    echo ERREUR: Setup non genere - version %VERSION%
    echo Fichiers presents dans le dossier courant:
    dir "Bay*.exe" 2>nul
    echo Fichiers presents dans electron-app\release:
    dir "electron-app\release\Bay*.exe" 2>nul
    pause
    exit /b 1
)

echo Setup trouve: %SETUP_FILE%

echo [4/7] Verification coherence versions
py sync_version.py --check "%VERSION%"
if errorlevel 1 (
    echo ERREUR: versions incoherentes apres build
    pause
    exit /b 1
)

if not exist "dist\BayBay\_internal\auto_updater.py" (
    echo ERREUR: artefact backend introuvable: dist\BayBay\_internal\auto_updater.py
    pause
    exit /b 1
)

findstr /c:"CURRENT_VERSION = \"%VERSION%\"" "dist\BayBay\_internal\auto_updater.py" >nul
if errorlevel 1 (
    echo ERREUR: backend compile non aligne sur la version %VERSION%
    pause
    exit /b 1
)

if /i "%PUBLISH_LOCAL_ONLY%"=="1" (
    echo Mode local uniquement active - arret avant Git et release.
    exit /b 0
)

echo [5/7] Git commit
git add -A
git commit -m "v%VERSION%"
git push origin main

echo [6/7] Git tag
git tag -a "v%VERSION%" -m "v%VERSION%"
git push origin "v%VERSION%"

echo [7/7] GitHub release
"%GH%" release create "v%VERSION%" "%SETUP_FILE%" --title "v%VERSION%" --notes "v%VERSION%"

echo RELEASE OK: https://github.com/mlk0622/BayBay/releases/tag/v%VERSION%
pause