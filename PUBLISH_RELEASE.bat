@echo off
chcp 65001 >nul 2>&1
title Bay Bay - Publier une Release
color 0E

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║            🚀 BAY BAY - Publier une nouvelle version         ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

:: Vérifier GitHub CLI
gh --version >nul 2>&1
if errorlevel 1 (
    echo ❌ GitHub CLI (gh) n'est pas installé
    echo.
    echo Installez-le: winget install GitHub.cli
    echo Puis: gh auth login
    pause
    exit /b 1
)

:: Vérifier l'authentification
gh auth status >nul 2>&1
if errorlevel 1 (
    echo ❌ Vous n'êtes pas connecté à GitHub
    echo Exécutez: gh auth login
    pause
    exit /b 1
)

echo ✅ GitHub CLI configuré
echo.

:: Lire la version actuelle depuis package.json
for /f "tokens=2 delims=:, " %%a in ('findstr /C:"\"version\"" electron-app\package.json') do set CURRENT_VERSION=%%~a
set CURRENT_VERSION=%CURRENT_VERSION:"=%
echo Version actuelle: %CURRENT_VERSION%
echo.

:: Demander la nouvelle version
set /p NEW_VERSION="Nouvelle version (ex: 2.2.0): "
if "%NEW_VERSION%"=="" (
    echo ❌ Version requise
    pause
    exit /b 1
)

echo.
echo ══════════════════════════════════════════════════════════════
echo  ÉTAPE 1: Mise à jour des numéros de version
echo ══════════════════════════════════════════════════════════════
echo.

:: Mettre à jour package.json
powershell -Command "(Get-Content 'electron-app\package.json') -replace '\"version\": \"%CURRENT_VERSION%\"', '\"version\": \"%NEW_VERSION%\"' | Set-Content 'electron-app\package.json'"
echo ✅ package.json mis à jour

:: Mettre à jour launcher.py
powershell -Command "(Get-Content 'launcher.py') -replace 'VERSION = \"[0-9.]+\"', 'VERSION = \"%NEW_VERSION%\"' | Set-Content 'launcher.py'"
echo ✅ launcher.py mis à jour

:: Mettre à jour main.js
powershell -Command "(Get-Content 'electron-app\main.js') -replace \"APP_VERSION = '[0-9.]+'\", \"APP_VERSION = '%NEW_VERSION%'\" | Set-Content 'electron-app\main.js'"
echo ✅ main.js mis à jour

echo.
echo ══════════════════════════════════════════════════════════════
echo  ÉTAPE 2: Build du backend Python
echo ══════════════════════════════════════════════════════════════
echo.

pyinstaller BayBay.spec --noconfirm >nul 2>&1
if errorlevel 1 (
    echo ❌ Erreur build Python
    pause
    exit /b 1
)
echo ✅ Backend Python compilé

echo.
echo ══════════════════════════════════════════════════════════════
echo  ÉTAPE 3: Build de l'application Electron
echo ══════════════════════════════════════════════════════════════
echo.

cd electron-app
if exist "release" rmdir /s /q "release"
call npm run build:win -- --publish never >nul 2>&1
if errorlevel 1 (
    echo ❌ Erreur build Electron
    cd ..
    pause
    exit /b 1
)
cd ..
echo ✅ Application Electron compilée

echo.
echo ══════════════════════════════════════════════════════════════
echo  ÉTAPE 4: Commit et push
echo ══════════════════════════════════════════════════════════════
echo.

git add -A
git commit -m "Release v%NEW_VERSION%"
git push origin main
echo ✅ Code poussé sur GitHub

echo.
echo ══════════════════════════════════════════════════════════════
echo  ÉTAPE 5: Création de la release GitHub
echo ══════════════════════════════════════════════════════════════
echo.

:: Créer le tag
git tag -a "v%NEW_VERSION%" -m "Version %NEW_VERSION%"
git push origin "v%NEW_VERSION%"
echo ✅ Tag v%NEW_VERSION% créé

:: Créer la release avec les fichiers
echo 📤 Upload des fichiers sur GitHub...

gh release create "v%NEW_VERSION%" ^
    "electron-app/release/Bay Bay Setup %NEW_VERSION%.exe#Bay-Bay-Setup-%NEW_VERSION%.exe" ^
    "electron-app/release/Bay Bay Setup %NEW_VERSION%.exe.blockmap#Bay-Bay-Setup-%NEW_VERSION%.exe.blockmap" ^
    "electron-app/release/latest.yml" ^
    --title "Bay Bay v%NEW_VERSION%" ^
    --notes "## 🏠 Bay Bay v%NEW_VERSION%

### Installation
Téléchargez et exécutez **Bay-Bay-Setup-%NEW_VERSION%.exe**

### Mise à jour automatique
Les utilisateurs existants recevront automatiquement cette mise à jour.

---
*Publié le %DATE%*"

if errorlevel 1 (
    echo ❌ Erreur création release
    echo.
    echo Essayez manuellement:
    echo   gh release create "v%NEW_VERSION%" --title "v%NEW_VERSION%"
    echo   Puis uploadez les fichiers sur https://github.com/mlk0622/BayBay/releases
    pause
    exit /b 1
)

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                   ✅ RELEASE PUBLIÉE!                        ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo Version %NEW_VERSION% publiée sur GitHub!
echo.
echo 📦 Fichiers uploadés:
echo    • Bay-Bay-Setup-%NEW_VERSION%.exe
echo    • Bay-Bay-Setup-%NEW_VERSION%.exe.blockmap
echo    • latest.yml
echo.
echo 🔗 URL: https://github.com/mlk0622/BayBay/releases/tag/v%NEW_VERSION%
echo.
echo Les utilisateurs recevront automatiquement la mise à jour!
echo.

pause
