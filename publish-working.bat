@echo off
title Bay Bay Publish Working
echo.
echo ========================================
echo      BAY BAY PUBLISH WORKING
echo ========================================
echo.

set GH="C:\Program Files\GitHub CLI\gh.exe"

REM Verifications
%GH% --version >nul 2>&1
if errorlevel 1 (
    echo X GitHub CLI non trouve
    pause
    exit /b 1
)

%GH% auth status >nul 2>&1
if errorlevel 1 (
    echo X Non authentifie GitHub
    pause
    exit /b 1
)

echo ✓ GitHub CLI OK

REM Lire version
cd "C:\Users\PC\OneDrive\Documents\PythonProject\gestion-locative"
for /f "tokens=2 delims=:, " %%a in ('findstr /C:"version" electron-app\package.json') do set CURRENT=%%~a
set CURRENT=%CURRENT:"=%
set CURRENT=%CURRENT: =%

echo Version actuelle: %CURRENT%
set /p NEW_VERSION="Nouvelle version: "

if "%NEW_VERSION%"=="" (
    echo X Version requise
    pause
    exit /b 1
)

echo.
echo [1/4] Mise a jour versions...

REM Mettre a jour versions
powershell -Command "(Get-Content 'electron-app\package.json') -replace '\"%CURRENT%\"', '\"%NEW_VERSION%\"' | Set-Content 'electron-app\package.json'"
powershell -Command "(Get-Content 'launcher.py') -replace 'VERSION = \"%CURRENT%\"', 'VERSION = \"%NEW_VERSION%\"' | Set-Content 'launcher.py'"
echo ✓ Versions mises a jour

echo.
echo [2/4] Build application...
call build-working.bat
if errorlevel 1 (
    echo X Erreur build
    pause
    exit /b 1
)

echo.
echo [3/4] Creation archive...
cd electron-app\dist-simple
for /d %%d in (*) do (
    set APP_DIR=%%d
    goto found
)
:found

powershell -Command "Compress-Archive -Path '%APP_DIR%\*' -DestinationPath 'BayBay-v%NEW_VERSION%.zip' -Force"
echo ✓ Archive creee: BayBay-v%NEW_VERSION%.zip

echo.
echo [4/4] Publication GitHub...
cd ..\..

git add -A
git commit -m "Release v%NEW_VERSION%"
git push origin main
git tag -a "v%NEW_VERSION%" -m "Version %NEW_VERSION%"
git push origin "v%NEW_VERSION%"

%GH% release create "v%NEW_VERSION%" "electron-app\dist-simple\BayBay-v%NEW_VERSION%.zip" --title "Bay Bay v%NEW_VERSION%" --notes "Version %NEW_VERSION% - Build automatique"

if errorlevel 1 (
    echo X Erreur release
    pause
    exit /b 1
)

echo.
echo ========================================
echo        RELEASE PUBLIEE !
echo ========================================
echo.
echo Version %NEW_VERSION% disponible sur GitHub
echo https://github.com/mlk0622/BayBay/releases
echo.

pause