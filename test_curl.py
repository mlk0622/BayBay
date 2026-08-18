import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('88.190.118.23', port=33000, username='baybay', password=r'B@yb@ylesafricains*!!09')
stdin, stdout, stderr = client.exec_command('curl -sI -H "Host: baybay.mb-site.com" http://127.0.0.1/')
print("Nginx Output:")
print(stdout.read().decode('utf-8'))
client.close()
