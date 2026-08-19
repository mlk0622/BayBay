import paramiko
import sys
import time

# Configuration de l'encodage pour Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

hostname = "88.190.118.23"
port = 33000
username = "baybay"
password = r"B@yb@ylesafricains*!!09"

def run_ssh_commands(client, commands):
    for cmd in commands:
        print(f"\nExécution : {cmd}")
        stdin, stdout, stderr = client.exec_command(cmd)
        
        if "sudo -S" in cmd:
            # Injecter le mot de passe dans stdin pour sudo
            stdin.write(password + "\n")
            stdin.flush()
            
        # Attendre la fin de l'exécution
        exit_status = stdout.channel.recv_exit_status()
        
        out_content = stdout.read().decode('utf-8')
        err_content = stderr.read().decode('utf-8')
        
        if out_content:
            print("--- STDOUT ---")
            print(out_content)
        if err_content:
            print("--- STDERR ---")
            print(err_content)
            
        print(f"Code de retour : {exit_status}")
        if exit_status != 0 and "git clone" not in cmd and "rm -rf" not in cmd:
            print(f"Erreur bloquante détectée (Code {exit_status})")
            return False
    return True

# Automatically push local git changes before deploy
import subprocess
try:
    print("Vérification et envoi des modifications locales sur GitHub...")
    subprocess.run(["git", "add", "."], check=False)
    subprocess.run(["git", "commit", "-m", "Auto-deploy commit"], check=False)
    subprocess.run(["git", "push", "origin", "main"], check=False)
except Exception as ge:
    print(f"Note Git push: {ge}")

try:
    print(f"Connexion à {hostname}:{port} en tant que {username}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname, port=port, username=username, password=password, timeout=10)
    print("!!! CONNEXION SSH RÉUSSIE !!!")
    
    # Liste des commandes à lancer sur le serveur
    commands = [
        # 1. Mettre à jour les paquets et installer les dépendances requises via sudo
        "sudo -S apt-get update",
        "sudo -S apt-get install -y git python3-venv python3-pip python3-full build-essential pkg-config libcairo2-dev python3-dev",
        
        # 2. Nettoyer l'ancien dossier
        "rm -rf /home/baybay/baybay",
        
        # 3. Cloner le repo
        "git clone https://github.com/mlk0622/BayBay.git /home/baybay/baybay",
        
        # 4. Créer l'environnement virtuel (avec python3-venv installé, ça marchera !)
        "python3 -m venv /home/baybay/baybay/venv",
        
        # 5. Mettre à jour pip et installer les dépendances
        "/home/baybay/baybay/venv/bin/pip install --upgrade pip",
        "/home/baybay/baybay/venv/bin/pip install -r /home/baybay/baybay/requirements.txt",
        "/home/baybay/baybay/venv/bin/pip install gunicorn",
        
        # 6. Créer le fichier .env
        "echo 'DATABASE_URL=mysql+pymysql://baybay:Zigotown*20251360*Efrei2030@88.190.118.23:33006/mabase' > /home/baybay/baybay/.env",
        "echo 'SECRET_KEY=baybay-cloud-secure-key-2026' >> /home/baybay/baybay/.env",
        
        # 7. Créer le dossier systemd utilisateur s'il n'existe pas
        "mkdir -p /home/baybay/.config/systemd/user",
        
        # 8. Écrire le fichier service systemd
        """cat << 'EOF' > /home/baybay/.config/systemd/user/baybay.service
[Unit]
Description=Gunicorn instance to serve Bay Bay
After=network.target

[Service]
WorkingDirectory=/home/baybay/baybay
Environment="PATH=/home/baybay/baybay/venv/bin"
ExecStart=/home/baybay/baybay/venv/bin/gunicorn --workers 3 --access-logfile - --bind 127.0.0.1:33082 app:app
Restart=always

[Install]
WantedBy=default.target
EOF""",
        
        # 9. Enable lingering so user services persist after SSH disconnect
        "sudo -S loginctl enable-linger baybay",
        
        # 10. Ensure firewall allows port 33081 and reload
        "sudo -S ufw allow 33081/tcp",
        "sudo -S ufw reload",
        
        # 11. Recharger systemd, lancer Gunicorn et redémarrer Nginx
        "systemctl --user daemon-reload",
        "systemctl --user enable baybay",
        "systemctl --user restart baybay",
        "sudo -S systemctl restart nginx",
        
        # 12. Vérifier le statut du service
        "systemctl --user status baybay | head -n 15",
        "sudo -S systemctl status nginx --no-pager | head -n 10"
    ]
    
    success = run_ssh_commands(client, commands)
    if success:
        print("\n🎉 DÉPLOIEMENT TERMINÉ AVEC SUCCÈS ! LE SERVEUR EST EN LIGNE SUR LE PORT 33081 !")
    else:
        print("\n❌ Le déploiement a échoué.")
        
    client.close()
except Exception as e:
    print("Erreur globale :", e)
    sys.exit(1)
