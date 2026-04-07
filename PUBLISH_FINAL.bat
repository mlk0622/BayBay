@echo off
chcp 65001 >nul 2>&1
title Bay Bay - Publication Automatique FINAL
color 0E

set GH_PATH="C:\Program Files\GitHub CLI\gh.exe"

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║          🚀 BAY BAY - Publication Automatique FINAL         ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

:: Vérifications préalables
echo 🔍 Vérifications...
%GH_PATH% --version >nul 2>&1
if errorlevel 1 (
    echo ❌ GitHub CLI non accessible
    pause
    exit /b 1
)

%GH_PATH% auth status >nul 2>&1
if errorlevel 1 (
    echo ❌ Non authentifié GitHub
    pause
    exit /b 1
)

%GH_PATH% repo view mlk0622/BayBay --json name >nul 2>&1
if errorlevel 1 (
    echo ❌ Repository non accessible
    pause
    exit /b 1
)
echo ✅ GitHub CLI configuré et opérationnel

:: Lire version actuelle
for /f "tokens=2 delims=:, " %%a in ('findstr /C:"\"version\"" electron-app\package.json') do set CURRENT_VERSION=%%~a
set CURRENT_VERSION=%CURRENT_VERSION:"=%
echo.
echo Version actuelle: %CURRENT_VERSION%

:: Demander nouvelle version
set /p NEW_VERSION="🎯 Nouvelle version (ex: 2.2.0): "
if "%NEW_VERSION%"=="" (
    echo ❌ Version requise
    pause
    exit /b 1
)

echo.
echo ══════════════════════════════════════════════════════════════
echo  📝 MISE À JOUR DES VERSIONS
echo ══════════════════════════════════════════════════════════════

:: Mise à jour des fichiers de version
powershell -Command "(Get-Content 'electron-app\package.json') -replace '\"version\": \"%CURRENT_VERSION%\"', '\"version\": \"%NEW_VERSION%\"' | Set-Content 'electron-app\package.json'"
powershell -Command "(Get-Content 'launcher.py') -replace 'VERSION = \"[0-9.]+\"', 'VERSION = \"%NEW_VERSION%\"' | Set-Content 'launcher.py'"
powershell -Command "(Get-Content 'electron-app\main.js') -replace \"APP_VERSION = '[0-9.]+'\", \"APP_VERSION = '%NEW_VERSION%'\" | Set-Content 'electron-app\main.js'"
powershell -Command "(Get-Content 'electron-app\splash.html') -replace 'Version [0-9.]+', 'Version %NEW_VERSION%' | Set-Content 'electron-app\splash.html'"
echo ✅ Versions mises à jour

echo.
echo ══════════════════════════════════════════════════════════════
echo  🔨 COMPILATION
echo ══════════════════════════════════════════════════════════════

:: Build Python
echo Backend Python...
pyinstaller BayBay.spec --noconfirm --distpath dist --workpath build
if errorlevel 1 (
    echo ❌ Erreur compilation Python
    pause
    exit /b 1
)

:: Build Electron
echo Application Electron...
cd electron-app
if exist "release" rmdir /s /q "release"
call npm run build:win -- --publish never
if errorlevel 1 (
    echo ❌ Erreur compilation Electron
    cd ..
    pause
    exit /b 1
)
cd ..

:: Vérifier fichiers
if not exist "electron-app\release\Bay Bay Setup %NEW_VERSION%.exe" (
    echo ❌ Installer manquant
    pause
    exit /b 1
)
if not exist "electron-app\release\latest.yml" (
    echo ❌ latest.yml manquant
    pause
    exit /b 1
)
echo ✅ Compilation terminée

echo.
echo ══════════════════════════════════════════════════════════════
echo  📤 PUBLICATION GITHUB
echo ══════════════════════════════════════════════════════════════

:: Commit et push
echo Git commit...
git add -A
git commit -m "🚀 Release v%NEW_VERSION%"
git push origin main

echo Tag création...
git tag -a "v%NEW_VERSION%" -m "Version %NEW_VERSION%"
git push origin "v%NEW_VERSION%"

:: Créer release
echo GitHub release...
%GH_PATH% release create "v%NEW_VERSION%" ^
    --title "🏠 Bay Bay v%NEW_VERSION%" ^
    --notes "## Bay Bay v%NEW_VERSION%

### 📥 Installation
Téléchargez et exécutez l'installateur ci-dessous.

### 🔄 Mise à jour automatique
Les utilisateurs existants recevront cette mise à jour automatiquement.

### 📋 Nouveautés
- [Décrivez les changements ici]

---
*Version publiée automatiquement le %DATE%*" ^
    --draft

if errorlevel 1 (
    echo ❌ Erreur création release
    pause
    exit /b 1
)

:: Upload fichiers
echo Upload fichiers...
%GH_PATH% release upload "v%NEW_VERSION%" "electron-app/release/Bay Bay Setup %NEW_VERSION%.exe"
%GH_PATH% release upload "v%NEW_VERSION%" "electron-app/release/latest.yml"

:: Publier
%GH_PATH% release edit "v%NEW_VERSION%" --draft=false

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                 🎉 RELEASE PUBLIÉE !                        ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo 🔗 https://github.com/mlk0622/BayBay/releases/tag/v%NEW_VERSION%
echo.
echo ✅ Version %NEW_VERSION% publiée avec succès
echo 📦 Installer: Bay Bay Setup %NEW_VERSION%.exe (%~z1 bytes)
echo 🔄 Auto-update activé via latest.yml
echo.

pause