@echo off
chcp 65001 >nul 2>&1
title Vérification Scripts - Bay Bay
color 0B

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║              ✅ SCRIPTS DE PUBLICATION PRÊTS                 ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

set GH_PATH="C:\Program Files\GitHub CLI\gh.exe"

echo 📊 État du système:
echo.

:: GitHub CLI
%GH_PATH% --version >nul 2>&1
if errorlevel 1 (
    echo ❌ GitHub CLI: NON DISPONIBLE
) else (
    echo ✅ GitHub CLI: INSTALLÉ
)

:: Authentification
%GH_PATH% auth status >nul 2>&1
if errorlevel 1 (
    echo ❌ GitHub Auth: NON CONNECTÉ
) else (
    echo ✅ GitHub Auth: CONNECTÉ
)

:: Repository
%GH_PATH% repo view mlk0622/BayBay --json name >nul 2>&1
if errorlevel 1 (
    echo ❌ Repository: INACCESSIBLE
) else (
    echo ✅ Repository: ACCESSIBLE
)

:: Fichiers de build
if exist "electron-app\release" (
    echo ✅ Dossier release: PRÉSENT
) else (
    echo ❌ Dossier release: MANQUANT
)

echo.
echo 📋 Scripts disponibles:
echo   • BUILD_ELECTRON.bat     - Compiler l'application
echo   • PUBLISH_FINAL.bat      - Publier une release complète
echo   • test_github_fixed.bat  - Tester GitHub CLI
echo.
echo 🎯 Pour publier une nouvelle version:
echo   1. Exécutez: BUILD_ELECTRON.bat
echo   2. Exécutez: PUBLISH_FINAL.bat
echo   3. Entrez le numéro de version (ex: 2.2.0)
echo.

pause