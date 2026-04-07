@echo off
chcp 65001 >nul 2>&1
title Bay Bay - Build Complet
color 0B

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║          🏠 BAY BAY - Build Application Complète             ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

:: Vérifications préliminaires
echo 🔍 Vérification des prérequis...
echo.

:: Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python n'est pas installé
    echo    Téléchargez-le: https://www.python.org/
    pause
    exit /b 1
)
echo ✅ Python:
python --version

:: Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js n'est pas installé
    echo    Téléchargez-le: https://nodejs.org/
    pause
    exit /b 1
)
echo ✅ Node.js:
node --version

:: npm
npm --version >nul 2>&1
if errorlevel 1 (
    echo ❌ npm n'est pas installé
    pause
    exit /b 1
)
echo ✅ npm:
npm --version

echo.
echo ══════════════════════════════════════════════════════════════
echo  ÉTAPE 1/3: Construction du Backend Python
echo ══════════════════════════════════════════════════════════════
echo.

:: Installer PyInstaller si nécessaire
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo 📦 Installation de PyInstaller...
    pip install pyinstaller --quiet
)

:: Installer les dépendances Python
echo 📦 Installation des dépendances Python...
pip install -r requirements.txt --quiet

:: Construire le backend
echo 🔨 Construction du backend...
pyinstaller BayBay.spec --noconfirm

if errorlevel 1 (
    echo ❌ Erreur lors de la construction du backend
    pause
    exit /b 1
)

echo ✅ Backend construit avec succès

echo.
echo ══════════════════════════════════════════════════════════════
echo  ÉTAPE 2/3: Préparation de l'Application Electron
echo ══════════════════════════════════════════════════════════════
echo.

cd electron-app

:: Installer les dépendances npm
if not exist "node_modules" (
    echo 📦 Installation des dépendances npm...
    call npm install
    if errorlevel 1 (
        echo ❌ Erreur d'installation npm
        cd ..
        pause
        exit /b 1
    )
) else (
    echo ✅ Dépendances npm déjà installées
)

echo.
echo ══════════════════════════════════════════════════════════════
echo  ÉTAPE 3/3: Construction de l'Application Electron
echo ══════════════════════════════════════════════════════════════
echo.

:: Nettoyer les anciens builds
if exist "release" (
    echo 🧹 Nettoyage...
    rmdir /s /q "release" 2>nul
)

:: Construire l'app Electron
echo 🔨 Construction de l'exécutable final...
echo    (Cela peut prendre plusieurs minutes)
echo.

call npm run build:win

if errorlevel 1 (
    echo ❌ Erreur lors de la construction Electron
    cd ..
    pause
    exit /b 1
)

cd ..

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                     ✅ BUILD RÉUSSI!                         ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo 📁 L'installateur se trouve dans:
echo    electron-app\release\
echo.
echo 📦 Fichiers générés:

if exist "electron-app\release\*.exe" (
    for %%f in (electron-app\release\*.exe) do echo    • %%~nxf
)

echo.
echo 💡 Instructions:
echo    1. Distribuez le fichier .exe aux utilisateurs
echo    2. Double-cliquez pour installer/lancer
echo    3. L'app se lance automatiquement sans console
echo.

pause
