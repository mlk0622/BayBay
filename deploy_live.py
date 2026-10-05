import os
import sys
import subprocess
import paramiko

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

def run_cmd(client, cmd, use_sudo=False):
    print(f"\n[SSH] {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd)
    if use_sudo or "sudo -S" in cmd:
        stdin.write(password + "\n")
        stdin.flush()
    status = stdout.channel.recv_exit_status()
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    if out:
        print(f"STDOUT:\n{out}")
    if err:
        print(f"STDERR:\n{err}")
    return status == 0

def main():
    print("=== DÉPLOIEMENT DU CORRECTIF DE BAYBAY SAAS ===")
    
    # 1. Création du bundle Git local
    bundle_path = os.path.join(os.path.dirname(__file__), "updates.bundle")
    if os.path.exists(bundle_path):
        os.remove(bundle_path)
    
    print("\n1. Création du bundle Git local depuis ae12c31...")
    res = subprocess.run(["git", "bundle", "create", "updates.bundle", "ae12c31..main"], capture_output=True, text=True)
    if res.returncode != 0:
        print("Erreur création bundle :", res.stderr)
        sys.exit(1)
    print("✅ Bundle créé avec succès !")

    # 2. Connexion SSH
    print(f"\n2. Connexion SSH à {hostname}:{port}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname, port=port, username=username, password=password, timeout=15)
    print("✅ Connexion SSH établie !")

    # 3. Transfert du bundle via SFTP
    print("\n3. Transfert SFTP du bundle vers le serveur...")
    sftp = client.open_sftp()
    remote_bundle = "/tmp/updates.bundle"
    sftp.put(bundle_path, remote_bundle)
    sftp.close()
    print("✅ Bundle transféré avec succès !")

    # 4. Application du bundle sur le dépôt distant
    print("\n4. Application des commits sur /home/baybay/baybay...")
    commands = [
        "git -C /home/baybay/baybay reset --hard HEAD",
        "git -C /home/baybay/baybay clean -fd",
        "git -C /home/baybay/baybay pull /tmp/updates.bundle main",
        "rm -f /tmp/updates.bundle",
        "git -C /home/baybay/baybay log -n 3 --oneline",
    ]
    for cmd in commands:
        if not run_cmd(client, cmd):
            print(f"❌ Échec de la commande : {cmd}")
            client.close()
            sys.exit(1)

    # 5. Synchronisation mb-site vers /var/www/html
    print("\n5. Synchronisation de mb-site...")
    run_cmd(client, "sudo -S cp -r /home/baybay/baybay/mb-site/* /var/www/html/", use_sudo=True)
    run_cmd(client, "sudo -S chown -R www-data:www-data /var/www/html", use_sudo=True)

    # 6. Redémarrage des services
    print("\n6. Redémarrage des services Gunicorn et Nginx...")
    run_cmd(client, "systemctl --user daemon-reload")
    run_cmd(client, "systemctl --user restart baybay")
    run_cmd(client, "sudo -S systemctl restart nginx", use_sudo=True)

    # 7. Vérification de l'état
    print("\n7. Vérification du statut du service baybay...")
    run_cmd(client, "systemctl --user is-active baybay")
    run_cmd(client, "curl -s -I http://127.0.0.1:33082/login | head -n 5")

    client.close()
    
    # Nettoyage local du bundle
    if os.path.exists(bundle_path):
        os.remove(bundle_path)
        
    print("\n🎉 DÉPLOIEMENT DU PORTAIL WEB RÉUSSI AVEC SUCCÈS !")

if __name__ == "__main__":
    main()
