import paramiko
import sys

hostname = "88.190.118.23"
port = 33000
username = "baybay"
password = r"B@yb@ylesafricains*!!09"
domain = "baybay.mb-site.com"

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

def run_ssh_commands(client, commands):
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
        if exit_status != 0:
            safe_print(f"Erreur bloquante sur : {cmd}")
            return False
    return True

baybay_service = """[Unit]
Description=Gunicorn instance to serve Bay Bay
After=network.target

[Service]
WorkingDirectory=/home/baybay/baybay
Environment="PATH=/home/baybay/baybay/venv/bin"
ExecStart=/home/baybay/baybay/venv/bin/gunicorn --workers 3 --access-logfile - --bind 127.0.0.1:33082 app:app
Restart=always

[Install]
WantedBy=default.target
"""

nginx_conf = f"""server {{
    listen 33081;
    server_name {domain} 88.190.118.23;

    client_max_body_size 100M;

    # Cloudflare Real-IP Headers Restoration
    set_real_ip_from 103.21.244.0/22;
    set_real_ip_from 103.22.200.0/22;
    set_real_ip_from 103.31.4.0/22;
    set_real_ip_from 141.101.64.0/18;
    set_real_ip_from 108.162.192.0/18;
    set_real_ip_from 190.93.240.0/20;
    set_real_ip_from 188.114.96.0/20;
    set_real_ip_from 197.234.240.0/22;
    set_real_ip_from 198.41.128.0/17;
    set_real_ip_from 162.158.0.0/15;
    set_real_ip_from 104.16.0.0/13;
    set_real_ip_from 104.24.0.0/14;
    set_real_ip_from 172.64.0.0/13;
    set_real_ip_from 131.0.72.0/22;
    set_real_ip_from 2606:4700::/32;
    set_real_ip_from 2803:f800::/32;
    set_real_ip_from 2405:b500::/32;
    set_real_ip_from 2405:8100::/32;
    set_real_ip_from 2a06:98c0::/29;
    set_real_ip_from 2c0f:f248::/32;
    real_ip_header CF-Connecting-IP;

    location / {{
        proxy_pass http://127.0.0.1:33082;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $http_x_forwarded_proto;
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
        with sftp.file('/home/baybay/.config/systemd/user/baybay.service', 'w') as f:
            f.write(baybay_service)
        with sftp.file('/tmp/baybay_nginx_33081.conf', 'w') as f:
            f.write(nginx_conf)
        sftp.close()

        commands = [
            # 1. Recharger le service Gunicorn utilisateur sur le port local 33082
            "systemctl --user daemon-reload",
            "systemctl --user restart baybay",

            # 2. Configurer Nginx pour écouter sur le port ouvert 33081 et proxifier vers 33082
            "sudo -S mv /tmp/baybay_nginx_33081.conf /etc/nginx/sites-available/baybay.mb-site.com",
            "sudo -S ln -sf /etc/nginx/sites-available/baybay.mb-site.com /etc/nginx/sites-enabled/",
            "sudo -S rm -f /etc/nginx/sites-enabled/default",

            # 3. Valider la syntaxe Nginx et redémarrer
            "sudo -S nginx -t",
            "sudo -S systemctl enable nginx",
            "sudo -S systemctl restart nginx",

            # 4. Vérifier les statuts des services
            "systemctl --user status baybay | head -n 10",
            "sudo -S systemctl status nginx --no-pager | head -n 10"
        ]

        run_ssh_commands(client, commands)
        client.close()
    except Exception as e:
        safe_print(f"Erreur d'exécution : {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
