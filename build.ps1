# Bay Bay - Build Script PowerShell
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Yellow
Write-Host "║          🏠 BAY BAY - Build Application Complète             ║" -ForegroundColor Yellow
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Yellow
Write-Host ""

# Changer le répertoire vers le projet
$projectPath = "C:\Users\PC\OneDrive\Documents\PythonProject\gestion-locative"
Set-Location -Path $projectPath
Write-Host "📁 Répertoire de travail: $projectPath" -ForegroundColor Green

# Vérifications
Write-Host "🔍 Vérification des prérequis..." -ForegroundColor Cyan

try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python non trouvé" -ForegroundColor Red
    exit 1
}

try {
    $nodeVersion = node --version 2>&1
    Write-Host "✅ Node.js: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Node.js non trouvé" -ForegroundColor Red
    exit 1
}

try {
    $npmVersion = npm --version 2>&1
    Write-Host "✅ npm: $npmVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ npm non trouvé" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "══════════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host " ÉTAPE 1/3: Construction du Backend Python" -ForegroundColor Yellow
Write-Host "══════════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

# Installer PyInstaller
Write-Host "📦 Vérification PyInstaller..." -ForegroundColor Cyan
$pyinstallerCheck = pip show pyinstaller 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "📦 Installation de PyInstaller..." -ForegroundColor Yellow
    pip install pyinstaller --quiet
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Erreur installation PyInstaller" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✅ PyInstaller installé" -ForegroundColor Green
}

# Installer les dépendances Python
Write-Host "📦 Installation des dépendances Python..." -ForegroundColor Cyan
pip install -r requirements.txt --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Erreur installation dépendances Python" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Dépendances Python installées" -ForegroundColor Green

# Build Python
Write-Host "🔨 Construction du backend Python..." -ForegroundColor Cyan
Write-Host "   Cela peut prendre quelques minutes..." -ForegroundColor Gray
pyinstaller BayBay.spec --noconfirm --distpath dist --workpath build
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Erreur construction backend Python" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Backend Python construit" -ForegroundColor Green

Write-Host ""
Write-Host "══════════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host " ÉTAPE 2/3: Préparation Electron" -ForegroundColor Yellow
Write-Host "══════════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

# Aller dans le dossier electron-app
Set-Location -Path "electron-app"
Write-Host "📁 Changement vers: $(Get-Location)" -ForegroundColor Gray

# Installer dépendances npm
if (-not (Test-Path "node_modules")) {
    Write-Host "📦 Installation des dépendances npm..." -ForegroundColor Cyan
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Erreur installation npm" -ForegroundColor Red
        Set-Location -Path ".."
        exit 1
    }
    Write-Host "✅ Dépendances npm installées" -ForegroundColor Green
} else {
    Write-Host "✅ Dépendances npm déjà présentes" -ForegroundColor Green
}

Write-Host ""
Write-Host "══════════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host " ÉTAPE 3/3: Construction Electron" -ForegroundColor Yellow
Write-Host "══════════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

# Nettoyer
if (Test-Path "release") {
    Write-Host "🧹 Nettoyage ancien build..." -ForegroundColor Cyan
    Remove-Item "release" -Recurse -Force
}

# Build Electron
Write-Host "🔨 Construction de l'application Electron..." -ForegroundColor Cyan
Write-Host "   Cela peut prendre 5-10 minutes..." -ForegroundColor Gray
npm run build:win
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Erreur construction Electron" -ForegroundColor Red
    Set-Location -Path ".."
    exit 1
}

# Retourner au dossier parent
Set-Location -Path ".."

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                     ✅ BUILD RÉUSSI!                         ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

# Afficher les résultats
Write-Host "📦 Fichiers générés:" -ForegroundColor Cyan
$releaseFiles = Get-ChildItem -Path "electron-app\release\*.exe" -ErrorAction SilentlyContinue
if ($releaseFiles) {
    foreach ($file in $releaseFiles) {
        $size = [math]::Round($file.Length / 1MB, 2)
        Write-Host "   • $($file.Name) ($size MB)" -ForegroundColor White
    }
} else {
    Write-Host "   ⚠️ Aucun fichier .exe trouvé" -ForegroundColor Yellow
}

$ymlFiles = Get-ChildItem -Path "electron-app\release\*.yml" -ErrorAction SilentlyContinue
if ($ymlFiles) {
    foreach ($file in $ymlFiles) {
        Write-Host "   • $($file.Name)" -ForegroundColor White
    }
}

Write-Host ""
Write-Host "📁 Dossier de sortie: electron-app\release\" -ForegroundColor Cyan
Write-Host ""

Read-Host "Appuyez sur Entrée pour continuer"