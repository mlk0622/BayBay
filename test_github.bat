@echo off
chcp 65001 >nul 2>&1
title Test GitHub CLI - Bay Bay
color 0B

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                🧪 TEST GITHUB CLI - BAY BAY                 ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

:: Tester GitHub CLI
echo 🔍 Test 1: Vérification GitHub CLI...
gh --version
if errorlevel 1 (
    echo ❌ GitHub CLI non installé
    echo Installez avec: winget install GitHub.cli
    pause
    exit /b 1
)
echo ✅ GitHub CLI installé

echo.
echo 🔍 Test 2: Vérification authentification...
gh auth status
if errorlevel 1 (
    echo ❌ Non authentifié
    echo Exécutez: gh auth login
    pause
    exit /b 1
)
echo ✅ Authentifié

echo.
echo 🔍 Test 3: Accès au repository...
gh repo view mlk0622/BayBay --json name,owner
if errorlevel 1 (
    echo ❌ Repository inaccessible
    echo Vérifiez que le repository mlk0622/BayBay existe
    pause
    exit /b 1
)
echo ✅ Repository accessible

echo.
echo 🔍 Test 4: Liste des releases existantes...
gh release list --repo mlk0622/BayBay --limit 5
echo.

echo ╔══════════════════════════════════════════════════════════════╗
echo ║               ✅ TOUS LES TESTS PASSÉS !                    ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo Vous pouvez maintenant utiliser PUBLISH_RELEASE.bat en toute sécurité.
echo.

pause