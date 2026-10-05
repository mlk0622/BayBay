import os
import sys
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

local_mb_dir = os.path.join(os.path.dirname(__file__), "mb-site")

def deploy_mb_site():
    print(f"Connexion SSH à {hostname}:{port}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname, port=port, username=username, password=password, timeout=15)
    
    sftp = client.open_sftp()
    
    # Create remote temp directory
    remote_tmp_dir = "/tmp/mb_site_upload"
    client.exec_command(f"rm -rf {remote_tmp_dir} && mkdir -p {remote_tmp_dir}")
    
    print("Envoi des fichiers de mb-site...")
    for root, dirs, files in os.walk(local_mb_dir):
        rel_path = os.path.relpath(root, local_mb_dir)
        remote_path = remote_tmp_dir if rel_path == "." else f"{remote_tmp_dir}/{rel_path.replace(os.sep, '/')}"
        
        # Ensure remote dir exists
        try:
            sftp.mkdir(remote_path)
        except IOError:
            pass
            
        for file in files:
            local_file = os.path.join(root, file)
            remote_file = f"{remote_path}/{file}"
            sftp.put(local_file, remote_file)
            
    sftp.close()
    print("Fichiers transférés dans /tmp. Synchronisation vers /var/www/html...")
    
    cmd = f"echo '{password}' | sudo -S cp -r {remote_tmp_dir}/* /var/www/html/ && echo '{password}' | sudo -S chown -R www-data:www-data /var/www/html && rm -rf {remote_tmp_dir}"
    stdin, stdout, stderr = client.exec_command(cmd)
    exit_status = stdout.channel.recv_exit_status()
    
    if exit_status == 0:
        print("✅ Synchronisation réussie vers /var/www/html !")
    else:
        print("❌ Erreur lors de la synchronisation :", stderr.read().decode())
        
    client.close()

if __name__ == "__main__":
    deploy_mb_site()
