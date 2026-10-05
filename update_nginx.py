import paramiko

conf = """# 1. Redirection 301 www -> apex (mb-site.com)
server {
    listen 80;
    listen [::]:80;
    listen 33081;
    listen [::]:33081;
    server_name www.mb-site.com;
    return 301 https://mb-site.com$request_uri;
}

# 2. Serveur principal mb-site.com
server {
    listen 80;
    listen [::]:80;
    listen 33081;
    listen [::]:33081;
    server_name mb-site.com;

    root /var/www/html;
    index index.html index.htm;

    client_max_body_size 100M;

    # Cloudflare Real-IP
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

    location = /robots.txt {
        default_type text/plain;
        charset utf-8;
        add_header Cache-Control "public, max-age=86400";
        try_files $uri =404;
    }

    location = /sitemap.xml {
        default_type application/xml;
        charset utf-8;
        add_header Cache-Control "public, max-age=3600";
        try_files $uri =404;
    }

    # Manifests PWA
    location ~* \.(webmanifest|json)$ {
        default_type application/manifest+json;
        charset utf-8;
        add_header Cache-Control "public, max-age=86400";
        try_files $uri =404;
    }

    # Favicons & Images statiques
    location ~* \.(ico|png|jpg|jpeg|svg|webp|gif)$ {
        expires 30d;
        add_header Cache-Control "public, max-age=2592000, immutable";
        try_files $uri =404;
    }

    # Styles & Scripts
    location ~* \.(css|js)$ {
        expires 7d;
        add_header Cache-Control "public, max-age=604800";
        try_files $uri =404;
    }

    # Polices de caracteres (Fonts)
    location ~* \.(woff|woff2|ttf|eot|otf)$ {
        expires 365d;
        add_header Cache-Control "public, max-age=31536000, immutable";
        add_header Access-Control-Allow-Origin "*";
        try_files $uri =404;
    }

    location /acces_prive_baybay {
        proxy_pass http://127.0.0.1:8082;
        proxy_http_version 1.1;
        proxy_set_header Host $host:$server_port;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # Documents HTML (Revalidation propre sans no-store)
    location / {
        add_header Cache-Control "public, max-age=0, must-revalidate";
        try_files $uri $uri.html $uri/ /index.html;
    }
}
"""

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('88.190.118.23', port=33000, username='baybay', password=r'B@yb@ylesafricains*!!09', timeout=10)

sftp = client.open_sftp()
with sftp.file('/tmp/mb_nginx_new.conf', 'w') as f:
    f.write(conf)
sftp.close()

cmd = 'echo B@yb@ylesafricains*!!09 | sudo -S mv /tmp/mb_nginx_new.conf /etc/nginx/sites-available/mb-site.com && echo B@yb@ylesafricains*!!09 | sudo -S nginx -t && echo B@yb@ylesafricains*!!09 | sudo -S systemctl reload nginx'
stdin, stdout, stderr = client.exec_command(cmd)
print('STDOUT:', stdout.read().decode())
print('STDERR:', stderr.read().decode())
client.close()
