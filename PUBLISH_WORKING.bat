@echo off
chcp 65001 >nul 2>&1
title Bay Bay - Publier une Release
color 0E

:: Définir le chemin vers GitHub CLI
set GH_PATH="C:\Program Files\GitHub CLI\gh.exe"

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║            🚀 BAY BAY - Publier une nouvelle version         ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

:: Vérifier GitHub CLI
echo 🔍 Vérification GitHub CLI...
%GH_PATH% --version
if errorlevel 1 (
    echo ❌ GitHub CLI (gh) n'est pas accessible
    echo.
    echo 📥 VÉRIFICATIONS:
    echo    1. GitHub CLI est-il installé ? winget install GitHub.cli
    echo    2. Chemin correct : C:\Program Files\GitHub CLI\gh.exe
    echo.
    pause
    exit /b 1
)
echo ✅ GitHub CLI trouvé

:: Vérifier l'authentification
echo 🔍 Vérification authentification GitHub...
%GH_PATH% auth status
if errorlevel 1 (
    echo ❌ Vous n'êtes pas connecté à GitHub
    echo.
    echo 🔐 AUTHENTIFICATION REQUISE:
    echo    Exécutez: %GH_PATH% auth login
    echo    Puis suivez les instructions à l'écran
    pause
    exit /b 1
)
echo ✅ Authentifié GitHub

:: Vérifier l'accès au repository
echo 🔍 Vérification accès repository...
%GH_PATH% repo view mlk0622/BayBay --json name >nul 2>&1
if errorlevel 1 (
    echo ❌ Impossible d'accéder au repository mlk0622/BayBay
    echo.
    echo 🔧 VÉRIFICATIONS:
    echo    1. Le repository existe-t-il sur GitHub ?
    echo    2. Avez-vous les droits d'écriture ?
    echo    3. Êtes-vous connecté au bon compte ?
    echo.
    echo 🔗 URL: https://github.com/mlk0622/BayBay
    pause
    exit /b 1
)
echo ✅ Repository accessible
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

:: Mettre à jour splash.html
powershell -Command "(Get-Content 'electron-app\splash.html') -replace 'Version [0-9.]+', 'Version %NEW_VERSION%' | Set-Content 'electron-app\splash.html'"
echo ✅ splash.html mis à jour

echo.
echo ══════════════════════════════════════════════════════════════
echo  ÉTAPE 2: Build du backend Python
echo ══════════════════════════════════════════════════════════════
echo.

echo 🔨 Compilation du backend Python...
pyinstaller BayBay.spec --noconfirm
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

echo 🔨 Compilation Electron...
cd electron-app
if exist "release" rmdir /s /q "release"
call npm run build:win -- --publish never
if errorlevel 1 (
    echo ❌ Erreur build Electron
    cd ..
    pause
    exit /b 1
)
cd ..
echo ✅ Application Electron compilée

:: Vérifier que les fichiers existent
if not exist "electron-app\release\Bay Bay Setup %NEW_VERSION%.exe" (
    echo ❌ Fichier Bay Bay Setup %NEW_VERSION%.exe manquant
    pause
    exit /b 1
)
if not exist "electron-app\release\latest.yml" (
    echo ❌ Fichier latest.yml manquant
    pause
    exit /b 1
)
echo ✅ Fichiers de release vérifiés

echo.
echo ══════════════════════════════════════════════════════════════
echo  ÉTAPE 4: Commit et push
echo ══════════════════════════════════════════════════════════════
echo.

echo 📝 Commit des changements...
git add -A
git commit -m "Release v%NEW_VERSION%"
if errorlevel 1 (
    echo ❌ Erreur lors du commit
    pause
    exit /b 1
)

echo 📤 Push vers GitHub...
git push origin main
if errorlevel 1 (
    echo ❌ Erreur lors du push
    pause
    exit /b 1
)
echo ✅ Code poussé sur GitHub

echo.
echo ══════════════════════════════════════════════════════════════
echo  ÉTAPE 5: Création de la release GitHub
echo ══════════════════════════════════════════════════════════════
echo.

:: Créer le tag
echo 🏷️ Création du tag v%NEW_VERSION%...
git tag -a "v%NEW_VERSION%" -m "Version %NEW_VERSION%"
if errorlevel 1 (
    echo ❌ Erreur création tag
    pause
    exit /b 1
)

git push origin "v%NEW_VERSION%"
if errorlevel 1 (
    echo ❌ Erreur push tag
    pause
    exit /b 1
)
echo ✅ Tag v%NEW_VERSION% créé

:: Créer la release avec les fichiers
echo 📦 Création de la release GitHub...
echo 📤 Upload des fichiers...

%GH_PATH% release create "v%NEW_VERSION%" ^
    "electron-app/release/Bay Bay Setup %NEW_VERSION%.exe" ^
    "electron-app/release/Bay Bay Setup %NEW_VERSION%.exe.blockmap" ^
    "electron-app/release/latest.yml" ^
    --title "Bay Bay v%NEW_VERSION%" ^
    --notes "## 🏠 Bay Bay v%NEW_VERSION%

### 📥 Installation
Téléchargez et exécutez **Bay-Bay-Setup-%NEW_VERSION%.exe**

### 🔄 Mise à jour automatique
Les utilisateurs existants recevront automatiquement cette mise à jour.

### 📋 Changelog
- [Ajoutez ici les modifications apportées]

---
*Publié automatiquement le %DATE% à %TIME%*"

if errorlevel 1 (
    echo ❌ Erreur création release
    echo.
    echo 🛠️ DEBUG - Fichiers disponibles:
    dir "electron-app\release"
    echo.
    echo 🔧 Essayez manuellement:
    echo   %GH_PATH% release create "v%NEW_VERSION%" --title "v%NEW_VERSION%"
    echo   Puis uploadez les fichiers sur https://github.com/mlk0622/BayBay/releases
    pause
    exit /b 1
)

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                   ✅ RELEASE PUBLIÉE!                        ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo 🎉 Version %NEW_VERSION% publiée avec succès sur GitHub!
echo.
echo 📦 Fichiers uploadés:
echo    • Bay Bay Setup %NEW_VERSION%.exe
echo    • Bay Bay Setup %NEW_VERSION%.exe.blockmap
echo    • latest.yml
echo.
echo 🔗 URL: https://github.com/mlk0622/BayBay/releases/tag/v%NEW_VERSION%
echo.
echo 🔄 Les utilisateurs recevront automatiquement la mise à jour!
echo.

pause