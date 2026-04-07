# 🏠 Bay Bay - Application de Gestion Immobilière

Application Electron + Flask pour la gestion de locations immobilières.

## ✨ Fonctionnalités

- 🏢 Gestion multi-SCI
- 🏠 Gestion des biens immobiliers
- 👤 Gestion des locataires
- 💰 Suivi des paiements
- 📄 Génération de quittances PDF
- 📧 Appels de loyer automatiques
- 📊 Tableau de bord récapitulatif
- 🔄 Mise à jour automatique via GitHub Releases

## 📦 Installation

### Pour les utilisateurs

1. Téléchargez `Bay Bay Setup 2.1.0.exe` depuis [GitHub Releases](https://github.com/mlk0622/BayBay/releases)
2. Exécutez l'installateur
3. L'application se lance automatiquement

### Pour les développeurs

**Prérequis :**
- Python 3.10+
- Node.js 18+
- Git

**Installation :**
```bash
# Cloner le repository
git clone https://github.com/mlk0622/BayBay.git
cd BayBay

# Installer les dépendances Python
pip install -r requirements.txt

# Lancer en mode développement
python launcher.py
```

## 🔨 Build de l'application

### Build automatique (recommandé)

```batch
BUILD_ELECTRON.bat
```

Ce script :
1. ✅ Compile le backend Python
2. ✅ Installe les dépendances npm
3. ✅ Construit l'application Electron
4. ✅ Génère l'installateur Windows

### Build manuel

```batch
# 1. Backend Python
pyinstaller BayBay.spec --noconfirm

# 2. Application Electron
cd electron-app
npm install
npm run build:win
```

**Résultat :** `electron-app/release/Bay Bay Setup 2.1.0.exe` (121 Mo)

## 🚀 Publier une nouvelle version

### Méthode automatique

```batch
PUBLISH_RELEASE.bat
```

Le script vous demandera :
- La nouvelle version (ex: 2.2.0)
- Mettra à jour tous les fichiers
- Construira l'application
- Créera la release GitHub avec auto-update

### Méthode manuelle

1. **Modifier les versions** dans :
   - `electron-app/package.json` → `"version": "2.2.0"`
   - `launcher.py` → `VERSION = "2.2.0"`
   - `electron-app/main.js` → `APP_VERSION = '2.2.0'`

2. **Build** :
   ```batch
   pyinstaller BayBay.spec --noconfirm
   cd electron-app
   npm run build:win -- --publish never
   ```

3. **Créer la release** :
   ```batch
   git add -A
   git commit -m "Release v2.2.0"
   git push origin main
   git tag -a "v2.2.0" -m "Version 2.2.0"
   git push origin "v2.2.0"

   # Upload sur GitHub
   gh release create "v2.2.0" \
     "electron-app/release/Bay Bay Setup 2.2.0.exe" \
     "electron-app/release/latest.yml" \
     --title "Bay Bay v2.2.0"
   ```

## 📂 Structure du projet

```
BayBay/
├── electron-app/              # Application Electron
│   ├── main.js               # Process principal
│   ├── splash.html           # Écran de chargement
│   ├── package.json          # Configuration npm
│   └── release/              # 📦 Exécutables générés
│
├── dist/BayBay/              # Backend Python compilé
├── BayBay.spec               # Config PyInstaller
├── launcher.py               # Lanceur Python
├── app.py                    # Application Flask
├── models/                   # Modèles de données
├── templates/                # Templates HTML
├── static/                   # CSS/JS
└── BUILD_ELECTRON.bat        # 🚀 Script de build
```

## 💾 Stockage des données

Les données sont stockées dans :
```
%APPDATA%\BayBay\
├── gestion_locative.db       # Base de données SQLite
├── .installed                # Marqueur d'installation
└── uploads/                  # Fichiers uploadés
    ├── assurances/
    ├── etats_lieux/
    ├── quittances/
    └── appels_loyer/
```

## 🔄 Mise à jour automatique

L'application vérifie automatiquement les mises à jour au démarrage.

**Configuration** : `electron-app/package.json`
```json
{
  "build": {
    "publish": {
      "provider": "github",
      "owner": "mlk0622",
      "repo": "BayBay"
    }
  }
}
```

## 📝 Changelog

### v2.1.0 (Actuelle)
- Renommage en "Bay Bay"
- Stockage des données dans %APPDATA%
- Auto-update via GitHub Releases
- Interface native Electron

## 📄 Licence

MIT License - Copyright © 2024 Bay Bay

## 🐛 Support

Pour signaler un bug ou suggérer une fonctionnalité :
https://github.com/mlk0622/BayBay/issues
