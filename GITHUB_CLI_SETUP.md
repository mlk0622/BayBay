# Guide d'installation GitHub CLI pour Bay Bay

## 📥 Installation de GitHub CLI

### Méthode 1: Avec winget (recommandée)
```batch
winget install GitHub.cli
```

### Méthode 2: Avec Chocolatey
```batch
choco install gh
```

### Méthode 3: Téléchargement manuel
1. Allez sur https://cli.github.com/
2. Téléchargez la version Windows
3. Installez le fichier .msi

## 🔐 Configuration

### 1. Redémarrez votre terminal CMD
Fermez et rouvrez votre fenêtre de commande

### 2. Vérifiez l'installation
```batch
gh --version
```

### 3. Authentifiez-vous
```batch
gh auth login
```

Suivez les instructions:
1. Sélectionnez "GitHub.com"
2. Choisissez "HTTPS"
3. Tapez "Y" pour authentification
4. Sélectionnez "Login with a web browser"
5. Copiez le code affiché
6. Appuyez sur Entrée pour ouvrir le navigateur
7. Connectez-vous sur GitHub et entrez le code

### 4. Testez l'accès au repository
```batch
gh repo view mlk0622/BayBay
```

## ✅ Scripts disponibles

Une fois GitHub CLI configuré, vous pouvez utiliser:

### PUBLISH_RELEASE.bat
- Script complet automatisé
- Met à jour les versions
- Compile l'application
- Publie automatiquement sur GitHub

### PUBLISH_SIMPLE.bat
- Version simplifiée
- Permet un contrôle étape par étape
- Option pour publication manuelle

### test_github.bat
- Teste que GitHub CLI fonctionne
- Vérifie l'accès au repository
- À utiliser en premier pour diagnostiquer

## 🐛 Dépannage

### "gh: command not found"
- Redémarrez votre terminal CMD
- Vérifiez que GitHub CLI est dans le PATH

### "Repository not found"
- Vérifiez que vous êtes connecté au bon compte GitHub
- Assurez-vous d'avoir accès au repository mlk0622/BayBay

### Erreurs d'authentification
- Re-lancez: `gh auth login`
- Vérifiez: `gh auth status`