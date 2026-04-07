# Bay Bay - Script de Build Simple et Fonctionnel

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║              🚀 BUILD BAY BAY SIMPLE                         ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

# Configuration
$projectPath = "C:\Users\PC\OneDrive\Documents\PythonProject\gestion-locative"
$electronPath = "$projectPath\electron-app"
$ghPath = "C:\Program Files\GitHub CLI\gh.exe"

Set-Location -Path $projectPath

Write-Host "📦 BUILD SIMPLE AVEC PowerShell" -ForegroundColor Cyan
Write-Host ""

# 1. Vérifier le backend Python
Write-Host "🔍 1/4 - Vérification backend Python..." -ForegroundColor Yellow
if (Test-Path "dist\BayBay\BayBay.exe") {
    Write-Host "✅ Backend Python trouvé" -ForegroundColor Green
} else {
    Write-Host "❌ Backend Python manquant" -ForegroundColor Red
    Write-Host "   Exécution de PyInstaller..." -ForegroundColor Gray
    & pyinstaller BayBay.spec --noconfirm --distpath dist --workpath build
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Erreur compilation Python" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Backend Python compilé" -ForegroundColor Green
}

# 2. Aller dans electron-app
Write-Host ""
Write-Host "🔍 2/4 - Configuration Electron..." -ForegroundColor Yellow
Set-Location -Path $electronPath

if (-not (Test-Path "node_modules")) {
    Write-Host "   Installation npm..." -ForegroundColor Gray
    & npm install --silent
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Erreur npm install" -ForegroundColor Red
        exit 1
    }
}
Write-Host "✅ Dépendances npm OK" -ForegroundColor Green

# 3. Build simple avec electron-packager
Write-Host ""
Write-Host "🔍 3/4 - Build avec electron-packager..." -ForegroundColor Yellow

# Installer electron-packager si nécessaire
$packagerCheck = & npm list electron-packager 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "   Installation electron-packager..." -ForegroundColor Gray
    & npm install electron-packager --save-dev
}

# Nettoyer et créer
if (Test-Path "build-output") {
    Remove-Item "build-output" -Recurse -Force
}

Write-Host "   Packaging avec electron-packager..." -ForegroundColor Gray
& npx electron-packager . "Bay Bay" --platform=win32 --arch=x64 --out=build-output --electron-version=32.3.3 --overwrite

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Packaging réussi" -ForegroundColor Green

    # Copier le backend
    $appDir = Get-ChildItem "build-output" -Directory | Select-Object -First 1
    if ($appDir) {
        $backendDest = "$($appDir.FullName)\resources\backend"
        Write-Host "   Copie du backend vers: $backendDest" -ForegroundColor Gray

        New-Item -Path $backendDest -ItemType Directory -Force | Out-Null
        Copy-Item -Path "..\dist\BayBay\*" -Destination $backendDest -Recurse -Force

        Write-Host "✅ Backend copié" -ForegroundColor Green

        # Afficher le résultat
        $exePath = "$($appDir.FullName)\Bay Bay.exe"
        if (Test-Path $exePath) {
            Write-Host ""
            Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
            Write-Host "║                    ✅ BUILD RÉUSSI !                         ║" -ForegroundColor Green
            Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Green
            Write-Host ""
            Write-Host "📁 Application créée dans: $($appDir.FullName)" -ForegroundColor Cyan
            Write-Host "🚀 Exécutable: Bay Bay.exe" -ForegroundColor White
            Write-Host ""
            Write-Host "💡 Pour tester: double-cliquez sur l'exécutable" -ForegroundColor Yellow
            Write-Host "📦 Pour distribuer: compressez le dossier entier" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "❌ Erreur packaging" -ForegroundColor Red
    exit 1
}

# 4. Option pour créer release GitHub
Write-Host ""
Write-Host "🔍 4/4 - Option GitHub Release..." -ForegroundColor Yellow
if (Test-Path $ghPath) {
    Write-Host "✅ GitHub CLI disponible" -ForegroundColor Green

    $createRelease = Read-Host "Créer une release GitHub ? (O/N)"
    if ($createRelease -eq "O" -or $createRelease -eq "o") {
        $version = Read-Host "Version (ex: 2.1.1)"
        if ($version) {
            Write-Host "   Compression de l'application..." -ForegroundColor Gray
            $zipPath = "Bay-Bay-v$version.zip"
            Compress-Archive -Path "$($appDir.FullName)\*" -DestinationPath $zipPath -Force

            Write-Host "   Création release GitHub..." -ForegroundColor Gray
            Set-Location -Path $projectPath

            & git add -A
            & git commit -m "Build v$version"
            & git push origin main
            & git tag -a "v$version" -m "Version $version"
            & git push origin "v$version"

            & $ghPath release create "v$version" "$electronPath\$zipPath" --title "Bay Bay v$version" --notes "Build automatique v$version"

            if ($LASTEXITCODE -eq 0) {
                Write-Host "✅ Release GitHub créée !" -ForegroundColor Green
            } else {
                Write-Host "❌ Erreur création release" -ForegroundColor Red
            }
        }
    }
} else {
    Write-Host "⚠️ GitHub CLI non disponible" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "✅ SCRIPT TERMINÉ" -ForegroundColor Green
Read-Host "Appuyez sur Entrée pour fermer"