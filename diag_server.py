import paramiko, sys, time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('88.190.118.23', port=33000, username='baybay', password='B@yb@ylesafricains*!!09', timeout=15)

# 1. Vérifier les logs Gunicorn récents (erreurs Python)
print("=" * 60)
print("1. LOGS GUNICORN RÉCENTS (erreurs)")
print("=" * 60)
stdin, stdout, stderr = ssh.exec_command(
    'journalctl --user -u baybay --since "5 minutes ago" --no-pager 2>&1 | tail -80'
)
time.sleep(3)
logs = stdout.read().decode('utf-8', errors='replace')
for line in logs.splitlines():
    if any(x in line.lower() for x in ['error', 'exception', 'traceback', '500', 'post']):
        print(line)

# 2. Tester POST /forgot-password avec un email réel qui existe en base
print("\n" + "=" * 60)
print("2. TEST POST /forgot-password avec email existant")
print("=" * 60)

# D'abord trouver un email existant
ssh.exec_command("""cat > /tmp/find_user.py << 'PYEOF'
import sys
sys.path.insert(0, '/home/baybay/baybay')
from app import app, db, User
with app.app_context():
    users = User.query.limit(5).all()
    for u in users:
        print(f"USER: {u.email}")
PYEOF""")
time.sleep(1)
stdin2, stdout2, stderr2 = ssh.exec_command('cd /home/baybay/baybay && ./venv/bin/python3 /tmp/find_user.py 2>&1')
time.sleep(3)
user_output = stdout2.read().decode('utf-8', errors='replace')
print("Utilisateurs en base:")
print(user_output)

# Extraire le premier email
test_email = None
for line in user_output.splitlines():
    if line.startswith('USER:'):
        test_email = line.split('USER:')[1].strip()
        break

if test_email:
    print(f"\nTest avec: {test_email}")
    
    # POST vers forgot-password via le serveur local (bypass Cloudflare)
    stdin3, stdout3, stderr3 = ssh.exec_command(
        f'curl -sv -c /tmp/fp_cookies.txt '
        f'-X POST http://127.0.0.1:33082/forgot-password '
        f'-d "email={test_email.replace("@", "%40")}" '
        f'-w "\\nHTTP_CODE:%{{http_code}}\\nFINAL_URL:%{{url_effective}}\\n" '
        f'-o /tmp/fp_response.html 2>&1'
    )
    time.sleep(5)
    curl_out = stdout3.read().decode('utf-8', errors='replace')
    for line in curl_out.splitlines():
        if any(x in line for x in ['HTTP_CODE', 'FINAL_URL', '< HTTP', 'Location', '302', '200', '500']):
            print(line)

    # Vérifier les messages flash dans la réponse
    ssh.exec_command("""cat > /tmp/extract_flash.py << 'PYEOF'
import re
try:
    c = open('/tmp/fp_response.html').read()
    # Messages flash
    msgs = re.findall(r'fa-circle-check|fa-triangle-exclamation|<span>(.*?)</span>', c, re.DOTALL)
    for m in msgs[:15]:
        if m and len(m.strip()) > 0 and len(m.strip()) < 300:
            print(f"FLASH: {m.strip()[:200]}")
    # Chercher le formulaire reset_password dans la réponse  
    if 'reset_password' in c or 'reset-password' in c:
        print("PAGE CONTIENT: reset_password")
    if 'forgot_password' in c or 'forgot-password' in c:
        print("PAGE CONTIENT: forgot_password")
    if 'code' in c.lower() and 'chiffres' in c.lower():
        print("PAGE CONTIENT: formulaire code à 6 chiffres")
except Exception as e:
    print(f"Erreur: {e}")
PYEOF""")
    time.sleep(1)
    stdin4, stdout4, stderr4 = ssh.exec_command('python3 /tmp/extract_flash.py 2>&1')
    time.sleep(2)
    print("\nContenu de la réponse:")
    print(stdout4.read().decode('utf-8', errors='replace'))

    # 3. Vérifier si un code a été créé en base
    print("\n" + "=" * 60)
    print("3. CODES EN BASE APRÈS forgot-password")
    print("=" * 60)
    ssh.exec_command(f"""cat > /tmp/check_codes.py << 'PYEOF'
import sys
sys.path.insert(0, '/home/baybay/baybay')
from app import app, db, EmailVerification
with app.app_context():
    all_v = EmailVerification.query.all()
    print(f"Total codes: {{len(all_v)}}")
    for v in all_v:
        print(f"  email={{v.email}} purpose={{v.purpose}} code={{v.code}} expires={{v.expires_at}}")
PYEOF""")
    time.sleep(1)
    stdin5, stdout5, stderr5 = ssh.exec_command('cd /home/baybay/baybay && ./venv/bin/python3 /tmp/check_codes.py 2>&1')
    time.sleep(3)
    print(stdout5.read().decode('utf-8', errors='replace'))

# 4. Tester POST /verify-email avec un code valide
print("\n" + "=" * 60)
print("4. TEST POST /verify-email")
print("=" * 60)
ssh.exec_command("""cat > /tmp/test_verify.py << 'PYEOF'
import sys
sys.path.insert(0, '/home/baybay/baybay')
from app import app, db, EmailVerification
with app.app_context():
    v = EmailVerification.query.filter_by(purpose='register').order_by(EmailVerification.id.desc()).first()
    if v:
        print(f"REGISTER_EMAIL={v.email}")
        print(f"REGISTER_CODE={v.code}")
        print(f"REGISTER_TOKEN={v.token}")
    else:
        print("NO_REGISTER_CODE")
PYEOF""")
time.sleep(1)
stdin6, stdout6, stderr6 = ssh.exec_command('cd /home/baybay/baybay && ./venv/bin/python3 /tmp/test_verify.py 2>&1')
time.sleep(3)
verify_info = stdout6.read().decode('utf-8', errors='replace')
print(verify_info)

reg_token = None
reg_code = None
for line in verify_info.splitlines():
    if line.startswith('REGISTER_TOKEN='):
        reg_token = line.split('=', 1)[1].strip()
    elif line.startswith('REGISTER_CODE='):
        reg_code = line.split('=', 1)[1].strip()

if reg_token and reg_code:
    print(f"\nTest verify-email avec token={reg_token[:20]}... code={reg_code}")
    stdin7, stdout7, stderr7 = ssh.exec_command(
        f'curl -sv -c /tmp/ve_cookies.txt -b /tmp/ve_cookies.txt '
        f'-X POST "http://127.0.0.1:33082/verify-email?token={reg_token}" '
        f'-d "code={reg_code}&token={reg_token}" '
        f'-w "\\nHTTP_CODE:%{{http_code}}\\nFINAL_URL:%{{url_effective}}\\n" '
        f'-o /tmp/ve_response.html 2>&1'
    )
    time.sleep(5)
    curl_out7 = stdout7.read().decode('utf-8', errors='replace')
    for line in curl_out7.splitlines():
        if any(x in line for x in ['HTTP_CODE', 'FINAL_URL', '< HTTP', 'Location', '302', '200', '500', 'set-cookie', 'remember']):
            print(line)

# 5. Regarder les logs Gunicorn APRÈS les tests
print("\n" + "=" * 60)
print("5. LOGS GUNICORN APRÈS TESTS")
print("=" * 60)
time.sleep(2)
stdin8, stdout8, stderr8 = ssh.exec_command(
    'journalctl --user -u baybay --since "1 minute ago" --no-pager 2>&1 | tail -30'
)
time.sleep(3)
print(stdout8.read().decode('utf-8', errors='replace'))

ssh.close()
