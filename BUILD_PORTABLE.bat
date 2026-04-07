@echo off
chcp 65001 >nul 2>&1
title Bay Bay - Build Fonctionnel
color 0A

set PROJECT_DIR=C:\Users\PC\OneDrive\Documents\PythonProject\gestion-locative
set ELECTRON_DIR=%PROJECT_DIR%\electron-app

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║              🚀 BUILD BAY BAY FONCTIONNEL                    ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

cd "%PROJECT_DIR%"

echo 📦 1/3 - Backend Python déjà compilé ✅
if not exist "dist\BayBay\BayBay.exe" (
    echo ❌ Backend manquant - exécutez d'abord:
    echo    pyinstaller BayBay.spec --noconfirm
    pause
    exit /b 1
)
echo    Backend trouvé: dist\BayBay\BayBay.exe

echo.
echo 📦 2/3 - Préparation Electron...
cd "%ELECTRON_DIR%"

if not exist "node_modules" (
    echo    Installation npm...
    npm install --silent
) else (
    echo    Dépendances npm ✅
)

echo.
echo 📦 3/3 - Création du package portable...

REM Nettoyer
if exist "portable" rmdir /s /q "portable"
mkdir "portable"

REM Copier Electron prebuilt
echo    Téléchargement Electron si nécessaire...
if not exist "node_modules\electron\dist" (
    echo ❌ Electron non trouvé dans node_modules
    pause
    exit /b 1
)

REM Créer la structure
mkdir "portable\resources"
mkdir "portable\resources\app"
mkdir "portable\resources\backend"

echo    Copie des fichiers Electron...
xcopy /Y "node_modules\electron\dist\*" "portable\" >nul
if exist "portable\electron.exe" ren "portable\electron.exe" "Bay Bay.exe"

echo    Copie de l'application...
copy /Y "main.js" "portable\resources\app\" >nul
copy /Y "splash.html" "portable\resources\app\" >nul
copy /Y "splash.css" "portable\resources\app\" >nul
copy /Y "package.json" "portable\resources\app\" >nul

echo    Copie du backend Python...
xcopy /E /Y "..\dist\BayBay\*" "portable\resources\backend\" >nul

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                    ✅ BUILD TERMINÉ !                        ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

echo 📁 Application créée dans: %ELECTRON_DIR%\portable\
echo 🚀 Exécutable: Bay Bay.exe

if exist "portable\Bay Bay.exe" (
    echo.
    echo 💡 Pour tester: double-cliquez sur "portable\Bay Bay.exe"
    echo 📦 Pour distribuer: compressez le dossier "portable"
) else (
    echo ❌ Erreur: Bay Bay.exe non créé
)

echo.
pause