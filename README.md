# 🏠 BayBay — Gestion Locative Intelligente & Sécurisée (v4.0)

<div align="center">

[![Version](https://img.shields.io/badge/version-4.0.0-blue.svg?style=for-the-badge&logo=appveyor)](https://github.com/mlk0622/BayBay/releases)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0.0-000000.svg?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Electron](https://img.shields.io/badge/Electron-Desktop-47848F.svg?style=for-the-badge&logo=electron&logoColor=white)](https://www.electronjs.org/)
[![Encryption](https://img.shields.io/badge/Security-AES--256-success.svg?style=for-the-badge&logo=shield)](https://github.com/mlk0622/BayBay)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](license.txt)

<br/>

**BayBay** est une suite logicielle tout-en-un de gestion immobilière moderne conçue pour les **propriétaires bailleurs particuliers** et les **sociétés civiles immobilières (SCI)**.  
Disponible en **application Bureau native Windows** et en **plateforme Web SaaS cloud**.

[🚀 Télécharger l'Installeur Windows (v4.0)](https://github.com/mlk0622/BayBay/releases/tag/v4.0) • [🌐 Accéder à la version Web](https://baybay.mb-site.com) • [👨‍💻 Site de l'auteur](https://mb-site.com)

</div>

---

## 📖 L'Histoire du Projet

> *"Ce projet est né d'un besoin concret : mon oncle cherchait une solution simple, moderne et centralisée pour piloter son parc locatif et ses SCI sans dépendre d'abonnements exorbitants ou d'outils obsolètes. Étudiant en 2ème année à l'EFREI Paris, j'ai décidé de prendre en charge l'intégralité de la conception et du développement de l'architecture logicielle, assisté par l'intelligence artificielle pour garantir une expérience utilisateur fluide et une sécurité optimale."*  
> — **Malik Bouaissi** ([mb-site.com](https://mb-site.com))

---

## ✨ Fonctionnalités Clés

### 📄 1. Génération Instantanée de Quittances ALUR
- Génération en 1 clic de **quittances de loyer officielles conformes à la loi ALUR**.
- Signature numérique intégrée du bailleur / de la SCI.
- Envoi direct et automatisé des quittances et avis d'échéance par email aux locataires.
- Format PDF vectoriel haute définition (généré via *ReportLab*).

### 🏢 2. Multi-Biens & Multi-SCI
- Gestion simultanée d'un nombre illimité de biens, appartements, parkings et locaux commerciaux.
- Prise en charge des SCI, indivisions et propriétés en nom propre.
- Baux personnalisables, gestion des dépôts de garantie, révision des loyers (IRL) et suivi des charges.

### 📊 3. Tableau de Bord Financier & Rentabilité
- Visualisation en temps réel des encaissements, loyers en attente et retards de paiement.
- Alertes automatiques en cas d'impayé.
- Calculs automatisés des revenus nets, des charges déductibles et bilan fiscal exportable.

### 🔐 4. Sécurité Avancée & Chiffrement 256 bits
- Chiffrement symétrique **AES-256 bits** des données sensibles et documents.
- Hachage robuste des mots de passe avec **Bcrypt + Salt**.
- Isolation des sessions utilisateurs et protection contre les failles CSRF, XSS et SQL Injection.

### 🔄 5. Double Mode : Bureau (Offline/Cloud) & Web (SaaS)
- **Version Bureau Windows** : Application Electron fluide avec démarrage instantané en arrière-plan, synchronisation optionnelle et mises à jour automatiques transparentes (*Auto-Updater*).
- **Version Web Cloud** : Accessible depuis n'importe quel navigateur sur smartphone, tablette ou PC via [baybay.mb-site.com](https://baybay.mb-site.com).

---

## 🛠️ Architecture & Stack Technique

```
┌─────────────────────────────────────────────────────────┐
│                    BayBay Platform                      │
├────────────────────────────┬────────────────────────────┤
│       Desktop Client       │         Web Client         │
│  (Electron.js + Native UI) │ (Tailwind CSS + Dark Glass)│
├────────────────────────────┴────────────────────────────┤
│                    Application Layer                    │
│            Python 3.11+ • Flask • Gunicorn              │
├────────────────────────────┬────────────────────────────┤
│      Database Layer        │     Security & Reports     │
│  MySQL / MariaDB / SQLite  │ ReportLab PDF • AES-256    │
└────────────────────────────┴────────────────────────────┘
```

| Composant | Technologie | Rôle |
| :--- | :--- | :--- |
| **Backend** | Python 3.11+, Flask, SQLAlchemy | Serveur d'application, API REST et logique métier |
| **Frontend** | HTML5, Tailwind CSS, JavaScript (ES6+) | Interface utilisateur Dark Glassmorphism |
| **Desktop Wrapper** | Electron.js, Node.js | Application bureau native Windows |
| **Génération PDF** | ReportLab, PyMuPDF | Quittances de loyer et documents officiels ALUR |
| **Base de Données** | MySQL, MariaDB, SQLite | Persistance et intégrité relationnelle |
| **Packaging** | PyInstaller, NSIS Setup Maker | Compilateur d'exécutable et installeur Windows |
| **Serveur & Proxy** | Linux Debian, Nginx, Gunicorn | Hébergement de production et reverse proxy |

---

## 🚀 Installation & Démarrage

### Option 1 : Utiliser l'Installeur Windows (Recommandé pour Bureau)

1. Rendez-vous sur la page des [Releases GitHub](https://github.com/mlk0622/BayBay/releases).
2. Téléchargez le fichier **`Bay.Bay.Setup.4.0.exe`**.
3. Lancez l'installeur et suivez les instructions.
4. L'application démarre automatiquement sur votre bureau !

---

### Option 2 : Lancer depuis les sources (Développement)

#### 1. Prérequis
- **Python 3.11** ou supérieur installé.
- **Node.js 18+** (optionnel, uniquement pour compiler la version Electron).
- **Git**.

#### 2. Cloner le projet
```bash
git clone https://github.com/mlk0622/BayBay.git
cd BayBay
```

#### 3. Installer les dépendances Python
```bash
python -m venv venv
# Windows :
venv\Scripts\activate
# Linux/macOS :
source venv/bin/activate

pip install -r requirements.txt
```

#### 4. Lancer le serveur local
```bash
python app.py
```
Ouvrez ensuite votre navigateur sur `http://127.0.0.1:5000`.

---

## 📦 Compilation de l'Installeur Bureau (.exe)

Pour compiler l'installeur Windows complet depuis les sources :

```bash
# 1. Compiler le backend Flask en standalone via PyInstaller
pyinstaller BayBay.spec

# 2. Synchroniser la version (ex: v4.0)
python sync_version.py 4.0

# 3. Compiler l'installeur final avec NSIS
makensis installer.nsi
```
Le fichier d'installation `Bay.Bay.Setup.4.0.exe` sera généré à la racine.

---

## 👤 Auteur & Crédits

- **Malik Bouaissi** — *Étudiant en 2ème année à l'EFREI Paris (École d'ingénieurs du numérique)*
  - Portfolio : [mb-site.com](https://mb-site.com)
  - GitHub : [@mlk0622](https://github.com/mlk0622)
  - Email : `contact@mb-site.com`

---

## 📄 Licence

Ce projet est distribué sous la licence [MIT](license.txt).
