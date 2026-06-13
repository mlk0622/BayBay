# Bay Bay - Guide Developpeur (Windows)

Application de gestion locative basee sur Flask (backend Python) + Electron (client desktop).

Ce README remplace l'ancienne doc et centralise les prerequis reels du projet, la procedure de build/publish, et les points a adapter sur une nouvelle machine.

## Fonctionnalites principales

- Gestion multi-SCI, biens, locataires
- Suivi des paiements et comptes locatifs
- Generation de quittances et appels de loyer PDF
- Stockage des donnees utilisateur dans `%APPDATA%\BayBay`
- Verification de mises a jour via GitHub Releases

## Prerequis developpeur

### 1) Python + Python Launcher (obligatoire)

Le projet utilise les commandes `py`, donc le Python Launcher Windows doit etre installe.

- Installer Python 3.10+ depuis https://www.python.org/downloads/windows/
- Pendant l'installation, cocher :
  - `Install launcher for all users (recommended)`
  - `Add python.exe to PATH`

Verification :

```powershell
py --version
py -m pip --version
```

Si `py` n'est pas reconnu, reinstall Python en activant bien le Launcher.

### 2) Node.js + npm (obligatoire)

- Installer Node.js 18+ (LTS recommande) : https://nodejs.org/

Verification :

```powershell
node -v
npm -v
```

### 3) NSIS (obligatoire pour generer le setup)

`build.bat` appelle `makensis.exe` pour creer l'installeur.

- Installer NSIS : https://nsis.sourceforge.io/Download
- Chemin attendu par defaut dans le script :
  - `C:\Program Files (x86)\NSIS\makensis.exe`

Si NSIS est installe ailleurs, modifier `build.bat` en consequence.

### 4) Git + GitHub CLI (obligatoire pour publish.bat)

- Installer Git : https://git-scm.com/download/win
- Installer GitHub CLI : https://cli.github.com/
- Se connecter :

```powershell
gh auth login
```

`publish.bat` utilise `gh release create`.

## Installation du projet (developpement)

Depuis PowerShell :

```powershell
git clone https://github.com/mlk0622/BayBay.git
cd BayBay

# Dependances Python
py -m pip install --upgrade pip
py -m pip install -r requirements.txt

# Dependances Electron
cd electron-app
npm install
cd ..
```

Lancement local :

```powershell
py launcher.py
```

## IMPORTANT - Adapter la racine locale dans les scripts BAT

Dans l'etat actuel du projet, les scripts utilisent un chemin absolu machine-specifique :

- `build.bat`
- `publish.bat`

Ils contiennent une ligne de ce type :

```bat
cd "C:\Users\<User>\Documents\>path>"
```

Sur une autre machine, cette ligne doit etre modifiee avec votre vrai chemin local du repo, sinon le build/publish echoue.

## Build local (installeur .exe)

Commande recommandee :

```powershell
build.bat
```

Le script effectue :

1. Build backend Python avec PyInstaller (`BayBay.spec`)
2. Packaging Electron (`@electron/packager`)
3. Copie du backend dans `electron-app/dist-simple/BayBay-win32-x64/resources/backend`
4. Creation de l'installeur NSIS via `installer.nsi`

Sortie attendue :

- `Bay.Bay.Setup.<version>.exe` a la racine du projet

## Publication d'une nouvelle version

Commande :

```powershell
publish.bat
```

Le script :

1. Demande une version (ex: `2.5.2`)
2. Met a jour les versions dans :
   - `electron-app/package.json`
   - `launcher.py`
   - `installer.nsi`
3. Lance `build.bat`
4. Commit + push + tag Git
5. Cree la release GitHub avec `gh`

## Fichiers de version a surveiller

Pour eviter les incoherences entre backend, setup et auto-update, verifier ces fichiers avant release :

- `launcher.py` (`VERSION = "..."`)
- `installer.nsi` (`!define APP_VERSION "..."`)
- `electron-app/package.json` (`"version": "..."`)
- `auto_updater.py` (`CURRENT_VERSION = "..."`) si la logique de comparaison de version en depend

## Arborescence utile

```text
BayBay/
|-- app.py
|-- launcher.py
|-- auto_updater.py
|-- BayBay.spec
|-- build.bat
|-- publish.bat
|-- installer.nsi
|-- requirements.txt
|-- electron-app/
|   |-- main.js
|   |-- package.json
|   `-- dist-simple/
|-- templates/
|-- static/
`-- models/
```

## Donnees utilisateur

Les donnees sont stockees hors dossier projet :

```text
%APPDATA%\BayBay\
|-- baybay.db
|-- .installed
`-- uploads/
```

Ce dossier est preserve lors des mises a jour applicatives.

## Depannage rapide

- `py` non reconnu : reinstall Python avec le Launcher active
- `makensis.exe` introuvable : installer NSIS ou corriger son chemin dans `build.bat`
- `gh` non reconnu : installer GitHub CLI puis `gh auth login`
- Build KO apres clone sur autre PC : verifier la racine locale configuree dans `build.bat` et `publish.bat`

## Licence

MIT License

## Support

Issues GitHub : https://github.com/mlk0622/BayBay/issues
