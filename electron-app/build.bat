@echo off
chcp 65001 >nul 2>&1
title Gestion Locative - Build Electron App
color 0B

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║      🏠 GESTION LOCATIVE - Build Application Electron        ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

:: Vérifier Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js n'est pas installé!
    echo.
    echo Téléchargez-le depuis: https://nodejs.org/
    pause
    exit /b 1
)
echo ✅ Node.js détecté:
node --version

:: Vérifier npm
npm --version >nul 2>&1
if errorlevel 1 (
    echo ❌ npm n'est pas installé!
    pause
    exit /b 1
)
echo ✅ npm détecté:
npm --version

echo.
echo ══════════════════════════════════════════════════════════════
echo  ÉTAPE 1: Construction du backend Python
echo ══════════════════════════════════════════════════════════════
echo.

:: Retourner au dossier parent pour builder le backend
cd ..

:: Vérifier si le backend est déjà construit
if not exist "dist\GestionLocative\GestionLocative.exe" (
    echo 📦 Construction du backend Python...

    pip show pyinstaller >nul 2>&1
    if errorlevel 1 (
        echo    Installation de PyInstaller...
        pip install pyinstaller --quiet
    )

    pip install -r requirements.txt --quiet
    pyinstaller GestionLocative.spec --noconfirm

    if errorlevel 1 (
        echo ❌ Erreur lors de la construction du backend
        pause
        exit /b 1
    )
) else (
    echo ✅ Backend déjà construit
)

echo.
echo ══════════════════════════════════════════════════════════════
echo  ÉTAPE 2: Installation des dépendances Electron
echo ══════════════════════════════════════════════════════════════
echo.

cd electron-app

:: Installer les dépendances npm
if not exist "node_modules" (
    echo 📦 Installation des dépendances npm...
    call npm install
    if errorlevel 1 (
        echo ❌ Erreur lors de l'installation des dépendances npm
        pause
        exit /b 1
    )
) else (
    echo ✅ Dépendances npm déjà installées
)

echo.
echo ══════════════════════════════════════════════════════════════
echo  ÉTAPE 3: Construction de l'application Electron
echo ══════════════════════════════════════════════════════════════
echo.

:: Nettoyer les anciens builds
if exist "release" (
    echo 🧹 Nettoyage des anciens builds...
    rmdir /s /q "release"
)

:: Construire l'application
echo 🔨 Construction de l'exécutable Windows...
call npm run build:win

if errorlevel 1 (
    echo ❌ Erreur lors de la construction
    pause
    exit /b 1
)

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                     ✅ BUILD RÉUSSI!                         ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo 📁 L'installateur se trouve dans:
echo    electron-app\release\
echo.
echo 📦 Fichiers générés:
dir /b release\*.exe 2>nul
echo.

pause
