# 🏠 Gestion Locative - Application Electron

## 📦 Fichiers générés

Après le build, vous trouverez dans `electron-app/release/`:

| Fichier | Description |
|---------|-------------|
| `Gestion Locative Setup 2.1.0.exe` | **Installateur Windows** - Double-cliquez pour installer |
| `win-unpacked/` | Version portable (pas besoin d'installer) |

---

## 🚀 Comment construire l'application

### Prérequis

1. **Python 3.10+** avec pip
2. **Node.js 18+** avec npm
3. **PyInstaller** (installé automatiquement)

### Build complet (recommandé)

Double-cliquez sur `BUILD_ELECTRON.bat` ou exécutez:

```batch
BUILD_ELECTRON.bat
```

Ce script:
1. ✅ Construit le backend Python avec PyInstaller
2. ✅ Installe les dépendances npm
3. ✅ Construit l'application Electron
4. ✅ Génère l'installateur Windows

### Build manuel

```batch
# 1. Construire le backend Python
pyinstaller GestionLocative.spec --noconfirm

# 2. Aller dans le dossier Electron
cd electron-app

# 3. Installer les dépendances
npm install

# 4. Construire l'application
npm run build:win
```

---

## 🎯 Fonctionnalités de l'application

### ✨ Interface native
- **Fenêtre dédiée** - Pas de navigateur externe
- **Splash screen** - Écran de chargement animé
- **Icône système** - L'app reste dans la barre des tâches

### 🔄 Auto-updater intégré
- Vérifie automatiquement les mises à jour au démarrage
- Notifications de nouvelle version
- Téléchargement et installation en un clic

### 🔇 Mode silencieux
- Pas de console visible
- Pas d'ouverture de navigateur
- Backend Python caché

---

## 📁 Structure du projet

```
gestion-locative/
├── electron-app/              # Application Electron
│   ├── main.js               # Process principal
│   ├── preload.js            # Bridge sécurisé
│   ├── splash.html           # Écran de chargement
│   ├── package.json          # Configuration npm
│   ├── build.bat             # Script de build
│   └── release/              # 📦 Exécutables générés
│       ├── *.exe             # Installateur
│       └── win-unpacked/     # Version portable
│
├── dist/GestionLocative/      # Backend Python compilé
├── GestionLocative.spec       # Config PyInstaller
├── launcher.py                # Lanceur Python
├── app.py                     # Application Flask
└── BUILD_ELECTRON.bat         # 🚀 Script de build complet
```

---

## 🔧 Configuration

### Changer la version

1. Modifier `VERSION` dans `launcher.py`
2. Modifier `version` dans `electron-app/package.json`
3. Modifier `APP_VERSION` dans `electron-app/main.js`

### Ajouter une icône personnalisée

1. Créez un fichier `icon.ico` (256x256 px minimum)
2. Placez-le dans `electron-app/build-resources/`
3. Décommentez les lignes `icon` dans `package.json`

### Configuration de l'auto-updater

Dans `electron-app/package.json`, ajoutez:

```json
{
  "build": {
    "publish": {
      "provider": "github",
      "owner": "VOTRE_USER",
      "repo": "gestion-locative"
    }
  }
}
```

---

## 🐛 Dépannage

### L'application ne démarre pas
- Vérifiez que le port 5000 n'est pas utilisé
- Lancez la version portable pour voir les erreurs

### Le backend ne se lance pas
- Vérifiez que `resources/backend/GestionLocative.exe` existe
- Testez le backend seul: `dist\GestionLocative\GestionLocative.exe`

### Erreur de build npm
```batch
# Nettoyer et réinstaller
cd electron-app
rmdir /s /q node_modules
del package-lock.json
npm install
```

---

## 📝 Notes

- L'application utilise le port **5000** par défaut
- Les données sont stockées dans le dossier de l'application
- La base SQLite est créée automatiquement au premier lancement
- L'icône dans la barre système permet de rouvrir l'app après fermeture
