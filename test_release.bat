@echo off
chcp 65001 >nul 2>&1
title Test Release - Bay Bay
color 0A

set GH_PATH="C:\Program Files\GitHub CLI\gh.exe"

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║              🧪 TEST CRÉATION RELEASE                        ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

:: Vérifier les fichiers existants
echo 📁 Vérification des fichiers de build...
if not exist "electron-app\release" (
    echo ❌ Dossier release manquant. Exécutez BUILD_ELECTRON.bat d'abord.
    pause
    exit /b 1
)

echo Fichiers disponibles dans electron-app\release:
dir "electron-app\release\*.exe"
dir "electron-app\release\*.yml"

echo.
echo Voulez-vous créer une release de test ? (O/N)
set /p CONTINUE=
if /i not "%CONTINUE%"=="O" (
    echo Annulé
    pause
    exit /b 0
)

:: Créer un tag de test
set TEST_VERSION=2.1.1
echo.
echo 🏷️ Création du tag de test v%TEST_VERSION%...
git tag -a "v%TEST_VERSION%" -m "Test release v%TEST_VERSION%"
git push origin "v%TEST_VERSION%"

echo.
echo 📦 Création de la release de test...
%GH_PATH% release create "v%TEST_VERSION%" ^
    --title "Bay Bay v%TEST_VERSION% (Test)" ^
    --notes "## 🧪 Version de test

Cette release est un test du système de publication automatique.

### Installation
Téléchargez et testez l'installateur.

---
*Test publié le %DATE%*" ^
    --draft

if errorlevel 1 (
    echo ❌ Erreur création release de test
    pause
    exit /b 1
)

echo ✅ Release de test créée comme DRAFT

echo.
echo 📤 Upload du fichier exe...
for %%f in ("electron-app\release\*.exe") do (
    echo Uploading %%f...
    %GH_PATH% release upload "v%TEST_VERSION%" "%%f"
    if errorlevel 1 (
        echo ❌ Erreur upload %%f
    ) else (
        echo ✅ %%f uploadé
    )
)

echo.
echo 📤 Upload latest.yml...
%GH_PATH% release upload "v%TEST_VERSION%" "electron-app\release\latest.yml"
if errorlevel 1 (
    echo ❌ Erreur upload latest.yml
) else (
    echo ✅ latest.yml uploadé
)

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║               ✅ RELEASE TEST CRÉÉE !                       ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo 🔗 Allez sur https://github.com/mlk0622/BayBay/releases
echo 📝 La release est en mode DRAFT - publiez-la manuellement pour tester
echo.

pause