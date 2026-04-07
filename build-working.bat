@echo off
title Bay Bay Build Final
echo.
echo ========================================
echo       BAY BAY BUILD WORKING
echo ========================================
echo.

REM Aller dans le dossier projet
cd "C:\Users\PC\OneDrive\Documents\PythonProject\gestion-locative"

REM 1. Verifier backend Python
echo [1/3] Verification backend Python...
if exist "dist\BayBay\BayBay.exe" (
    echo ✓ Backend Python OK
) else (
    echo ! Backend manquant - compilation...
    pyinstaller BayBay.spec --noconfirm
    if errorlevel 1 (
        echo X Erreur backend
        pause
        exit /b 1
    )
    echo ✓ Backend compile
)

REM 2. Aller dans electron-app
echo.
echo [2/3] Preparation Electron...
cd electron-app

REM Installer electron-packager
npm list electron-packager >nul 2>&1
if errorlevel 1 (
    echo   Installation electron-packager...
    npm install electron-packager
)

REM Nettoyer
if exist "dist-simple" rmdir /s /q "dist-simple"

REM 3. Build simple
echo.
echo [3/3] Build application...
echo   Cela peut prendre quelques minutes...

npx electron-packager . BayBay --platform=win32 --arch=x64 --out=dist-simple --overwrite --no-prune

if errorlevel 1 (
    echo X Erreur build
    pause
    exit /b 1
)

REM Copier le backend
echo   Copie backend...
for /d %%d in (dist-simple\*) do (
    if not exist "%%d\resources\backend" mkdir "%%d\resources\backend"
    xcopy "..\dist\BayBay\*" "%%d\resources\backend\" /E /Y
    echo ✓ Application prete: %%d\BayBay.exe
)

echo.
echo ========================================
echo           BUILD TERMINE !
echo ========================================
echo.
echo Dossier: electron-app\dist-simple\
echo.

pause