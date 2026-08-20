import paramiko, sys, time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('88.190.118.23', port=33000, username='baybay', password='B@yb@ylesafricains*!!09', timeout=15)

# 1. Vérifier le formulaire verify_email: action POST et champs
ssh.exec_command("cat > /tmp/check_verify.py << 'PYEOF'\nimport re\ntry:\n    c = open('/home/baybay/baybay/templates/verify_email.html').read()\n    # Trouver le form action et les input\n    forms = re.findall(r'<form[^>]*>', c)\n    inputs = re.findall(r'<input[^>]*name=[^>]+>', c)\n    print('FORMS:', forms)\n    print('INPUTS:', inputs)\nexcept Exception as e:\n    print('Erreur:', e)\nPYEOF\n")
time.sleep(1)
stdin1, stdout1, stderr1 = ssh.exec_command("python3 /tmp/check_verify.py 2>&1")
time.sleep(2)
print("=== FORMULAIRE VERIFY_EMAIL ===")
print(stdout1.read().decode('utf-8', errors='replace'))

# 2. Tester POST verify-email avec un code valide depuis la base
# email=mbouaissi53@gmail.com, code=880095
print("\n=== TEST POST /verify-email ===")
stdin2, stdout2, stderr2 = ssh.exec_command(
    "curl -sv -c /tmp/vc.txt -b /tmp/vc.txt "
    "-X POST 'https://baybay.mb-site.com/verify-email' "
    "-d 'email=mbouaissi53%40gmail.com&code=880095' "
    "-w '\\nHTTP_CODE:%{http_code}\\nFINAL_URL:%{url_effective}\\n' "
    "-o /tmp/vr.html 2>&1"
)
time.sleep(5)
out2 = stdout2.read().decode('utf-8', errors='replace')
# Extraire juste les lignes HTTP importantes
for line in out2.splitlines():
    if any(x in line for x in ['HTTP_CODE', 'FINAL_URL', 'Location', '< HTTP', 'Redirect', '302', '200']):
        print(line)

# 3. Tester aussi avec token dans l'URL
ssh.exec_command("cat > /tmp/get_token.py << 'PYEOF'\nimport sys\nsys.path.insert(0, '/home/baybay/baybay')\nfrom app import app, db, EmailVerification\nwith app.app_context():\n    v = EmailVerification.query.filter_by(email='mbouaissi53@gmail.com', purpose='register').first()\n    if v:\n        print(f'TOKEN={v.token}')\n        print(f'CODE={v.code}')\n    else:\n        print('NOT FOUND')\nPYEOF\n")
time.sleep(1)
stdin3, stdout3, stderr3 = ssh.exec_command("cd /home/baybay/baybay && ./venv/bin/python3 /tmp/get_token.py 2>&1")
time.sleep(3)
result = stdout3.read().decode('utf-8', errors='replace')
print("\n=== TOKEN/CODE POUR mbouaissi53 ===")
print(result)

token = None
code = None
for line in result.splitlines():
    if line.startswith('TOKEN='):
        token = line.split('=', 1)[1].strip()
    elif line.startswith('CODE='):
        code = line.split('=', 1)[1].strip()

if token and code:
    print(f"\n=== TEST POST /verify-email avec TOKEN dans URL ===")
    stdin4, stdout4, stderr4 = ssh.exec_command(
        f"curl -sv -c /tmp/vc2.txt -b /tmp/vc2.txt "
        f"-X POST 'https://baybay.mb-site.com/verify-email?token={token}' "
        f"-d 'code={code}&token={token}' "
        f"-w '\\nHTTP_CODE:%%{{http_code}}\\nFINAL_URL:%%{{url_effective}}\\n' "
        f"-o /tmp/vr2.html 2>&1"
    )
    time.sleep(5)
    out4 = stdout4.read().decode('utf-8', errors='replace')
    for line in out4.splitlines():
        if any(x in line for x in ['HTTP_CODE', 'FINAL_URL', 'Location', '< HTTP', '302', '200', 'dashboard', 'app']):
            print(line)
    
    # Regarder les messages flash dans la réponse
    stdin5, stdout5, stderr5 = ssh.exec_command(
        "python3 -c \"import re; c=open('/tmp/vr2.html').read(); "
        "msgs=re.findall(r'<span>(.*?)</span>', c, re.DOTALL); "
        "[print(m.strip()[:300]) for m in msgs[:10]]\""
    )
    time.sleep(2)
    print("\n=== MESSAGES APRES SOUMISSION CODE ===")
    print(stdout5.read().decode('utf-8', errors='replace'))

# 4. Chercher erreurs Python recentes dans les logs
stdin6, stdout6, stderr6 = ssh.exec_command(
    "journalctl --user -u baybay --since '10 minutes ago' --no-pager 2>&1 | "
    "grep -A3 -B1 'Error\\|Exception\\|Traceback' | head -60"
)
time.sleep(2)
print("\n=== ERREURS RECENTES GUNICORN ===")
print(stdout6.read().decode('utf-8', errors='replace'))

ssh.close()
