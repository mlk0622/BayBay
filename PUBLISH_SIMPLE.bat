@echo off
chcp 65001 >nul 2>&1
title Bay Bay - Publication Simple
color 0A

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║         🚀 BAY BAY - Publication Simple (Manuel)            ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

:: Lire la version actuelle
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
echo  MISE À JOUR DES VERSIONS
echo ══════════════════════════════════════════════════════════════
echo.

:: 1. Mettre à jour package.json
powershell -Command "(Get-Content 'electron-app\package.json') -replace '\"version\": \"%CURRENT_VERSION%\"', '\"version\": \"%NEW_VERSION%\"' | Set-Content 'electron-app\package.json'"
echo ✅ package.json: %CURRENT_VERSION% → %NEW_VERSION%

:: 2. Mettre à jour launcher.py
powershell -Command "(Get-Content 'launcher.py') -replace 'VERSION = \"[0-9.]+\"', 'VERSION = \"%NEW_VERSION%\"' | Set-Content 'launcher.py'"
echo ✅ launcher.py: VERSION = "%NEW_VERSION%"

:: 3. Mettre à jour main.js
powershell -Command "(Get-Content 'electron-app\main.js') -replace \"APP_VERSION = '[0-9.]+'\", \"APP_VERSION = '%NEW_VERSION%'\" | Set-Content 'electron-app\main.js'"
echo ✅ main.js: APP_VERSION = '%NEW_VERSION%'

:: 4. Mettre à jour splash.html
powershell -Command "(Get-Content 'electron-app\splash.html') -replace 'Version [0-9.]+', 'Version %NEW_VERSION%' | Set-Content 'electron-app\splash.html'"
echo ✅ splash.html: Version %NEW_VERSION%

echo.
echo ══════════════════════════════════════════════════════════════
echo  COMPILATION
echo ══════════════════════════════════════════════════════════════
echo.

:: Build Python
echo 🔨 Compilation du backend Python...
pyinstaller BayBay.spec --noconfirm
if errorlevel 1 (
    echo ❌ Erreur compilation Python
    pause
    exit /b 1
)
echo ✅ Backend Python compilé

:: Build Electron
echo 🔨 Compilation Electron...
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
echo ✅ Application Electron compilée

:: Vérifier les fichiers
if not exist "electron-app\release\Bay Bay Setup %NEW_VERSION%.exe" (
    echo ❌ Fichier Bay Bay Setup %NEW_VERSION%.exe manquant
    pause
    exit /b 1
)
echo ✅ Fichier installer créé: Bay Bay Setup %NEW_VERSION%.exe

echo.
echo ══════════════════════════════════════════════════════════════
echo  PRÊT POUR PUBLICATION
echo ══════════════════════════════════════════════════════════════
echo.

echo 📦 Fichiers générés:
echo    • electron-app\release\Bay Bay Setup %NEW_VERSION%.exe
echo    • electron-app\release\latest.yml
echo.

echo 🔄 Pour publier sur GitHub:
echo    1. Committez les changements: git add -A ^&^& git commit -m "Release v%NEW_VERSION%"
echo    2. Poussez: git push origin main
echo    3. Créez un tag: git tag v%NEW_VERSION% ^&^& git push origin v%NEW_VERSION%
echo    4. Créez une release sur GitHub avec les fichiers ci-dessus
echo.

echo Voulez-vous continuer automatiquement ? (O/N)
set /p CONTINUE=
if /i "%CONTINUE%"=="O" (
    echo.
    echo Commit et push...
    git add -A
    git commit -m "Release v%NEW_VERSION%"
    git push origin main
    git tag -a "v%NEW_VERSION%" -m "Version %NEW_VERSION%"
    git push origin "v%NEW_VERSION%"
    echo ✅ Code poussé sur GitHub

    echo.
    echo 📱 Pour terminer:
    echo    Allez sur https://github.com/mlk0622/BayBay/releases
    echo    Cliquez "Create a new release"
    echo    Sélectionnez le tag v%NEW_VERSION%
    echo    Uploadez le fichier Bay Bay Setup %NEW_VERSION%.exe
    echo    Uploadez le fichier latest.yml
    echo    Publiez la release
) else (
    echo.
    echo ℹ️ Compilation terminée. Suivez les étapes manuellement.
)

echo.
pause