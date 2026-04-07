@echo off
chcp 65001 >nul 2>&1
title Test GitHub CLI - Bay Bay
color 0B

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                🧪 TEST GITHUB CLI - BAY BAY                 ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

:: Définir le chemin vers GitHub CLI
set GH_PATH="C:\Program Files\GitHub CLI\gh.exe"

:: Tester GitHub CLI
echo 🔍 Test 1: Vérification GitHub CLI...
%GH_PATH% --version
if errorlevel 1 (
    echo ❌ GitHub CLI non accessible
    echo Chemin testé: %GH_PATH%
    pause
    exit /b 1
)
echo ✅ GitHub CLI trouvé

echo.
echo 🔍 Test 2: Vérification authentification...
%GH_PATH% auth status
if errorlevel 1 (
    echo ❌ Non authentifié
    echo.
    echo Pour vous authentifier:
    echo %GH_PATH% auth login
    echo.
    pause
    exit /b 1
)
echo ✅ Authentifié

echo.
echo 🔍 Test 3: Accès au repository...
%GH_PATH% repo view mlk0622/BayBay --json name,owner
if errorlevel 1 (
    echo ❌ Repository inaccessible
    echo Vérifiez que le repository mlk0622/BayBay existe
    pause
    exit /b 1
)
echo ✅ Repository accessible

echo.
echo 🔍 Test 4: Liste des releases existantes...
%GH_PATH% release list --repo mlk0622/BayBay --limit 5

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║               ✅ TOUS LES TESTS PASSÉS !                    ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

pause