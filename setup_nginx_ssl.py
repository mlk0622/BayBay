import paramiko
import sys

# Configuration SSH
hostname = "88.190.118.23"
port = 33000
username = "baybay"
password = r"B@yb@ylesafricains*!!09"
domain = "baybay.mb-site.com"
backend_url = "http://127.0.0.1:33081"

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

def safe_print(text):
    try:
        print(text)
    except Exception:
        print(text.encode('ascii', errors='replace').decode('ascii'))

def run_ssh_commands(client, commands, ignore_errors=False):
    for cmd in commands:
        safe_print(f"\nExécution : {cmd}")
        stdin, stdout, stderr = client.exec_command(cmd)
        
        if "sudo -S" in cmd:
            stdin.write(password + "\n")
            stdin.flush()
            
        exit_status = stdout.channel.recv_exit_status()
        out_content = stdout.read().decode('utf-8', errors='replace')
        err_content = stderr.read().decode('utf-8', errors='replace')
        
        if out_content:
            safe_print("--- STDOUT ---")
            safe_print(out_content)
        if err_content:
            safe_print("--- STDERR ---")
            safe_print(err_content)
            
        safe_print(f"Code de retour : {exit_status}")
        if exit_status != 0 and not ignore_errors:
            safe_print(f"Avertissement sur : {cmd}")
    return True

nginx_initial_conf = f"""server {{
    listen 80;
    server_name {domain};

    client_max_body_size 100M;

    location /.well-known/acme-challenge/ {{
        root /var/www/certbot;
    }}

    location / {{
        proxy_pass {backend_url};
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }}
}}"""

def main():
    try:
        safe_print(f"Connexion SSH à {hostname}:{port}...")
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname, port=port, username=username, password=password, timeout=15)
        safe_print("Connexion SSH établie !")

        sftp = client.open_sftp()
        with sftp.file('/tmp/baybay_nginx.conf', 'w') as f:
            f.write(nginx_initial_conf)
        sftp.close()

        commands = [
            # 1. Arrêter Apache2 pour libérer le port 80
            "sudo -S systemctl stop apache2",
            "sudo -S systemctl disable apache2",

            # 2. Créer le dossier pour le challenge Certbot webroot
            "sudo -S mkdir -p /var/www/certbot",
            "sudo -S chown -R www-data:www-data /var/www/certbot",

            # 3. Installer Nginx, Certbot et le plugin Certbot-Nginx
            "sudo -S apt-get update",
            "sudo -S apt-get install -y nginx certbot python3-certbot-nginx",

            # 4. Autoriser le trafic HTTP (80) et HTTPS (443) dans le pare-feu
            "sudo -S ufw allow 80/tcp",
            "sudo -S ufw allow 443/tcp",
            "sudo -S ufw reload",

            # 5. Déplacer la configuration Nginx dans sites-available
            "sudo -S mv /tmp/baybay_nginx.conf /etc/nginx/sites-available/baybay.mb-site.com",
            "sudo -S ln -sf /etc/nginx/sites-available/baybay.mb-site.com /etc/nginx/sites-enabled/",
            "sudo -S rm -f /etc/nginx/sites-enabled/default",

            # 6. Tester et redémarrer Nginx
            "sudo -S nginx -t",
            "sudo -S systemctl enable nginx",
            "sudo -S systemctl restart nginx",

            # 7. Tenter l'obtention du certificat SSL avec Certbot webroot
            f"sudo -S certbot certonly --webroot -w /var/www/certbot -d {domain} --non-interactive --agree-tos --register-unsafely-without-email",

            # 8. Alternative Certbot --nginx au cas où
            f"sudo -S certbot --nginx -d {domain} --non-interactive --agree-tos --register-unsafely-without-email --redirect",

            # 9. Activer le renouvellement automatique Certbot
            "sudo -S systemctl enable --now certbot.timer",

            # 10. Statut final Nginx
            "sudo -S systemctl status nginx --no-pager | head -n 15"
        ]

        run_ssh_commands(client, commands, ignore_errors=True)
        safe_print(f"\n🎉 EXÉCUTION TERMINÉE POUR {domain} !")
        client.close()
    except Exception as e:
        safe_print(f"Erreur d'exécution : {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
