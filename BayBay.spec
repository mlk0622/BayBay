# -*- mode: python ; coding: utf-8 -*-
# BayBay.spec - Configuration PyInstaller avec Auto-Update
# ==================================================================
#
# COMMANDE POUR CONSTRUIRE L'EXECUTABLE:
#
#   pyinstaller BayBay.spec --noconfirm
#
# OU utiliser le script batch:
#
#   build_exe.bat
#
# ==================================================================

import os
import sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# Chemin de base du projet
BASE_PATH = os.path.dirname(os.path.abspath(SPEC))

# ========== COLLECTE DES DONNÉES ==========

# Fichiers Python de l'application
app_files = [
    ('app.py', '.'),
    ('auto_updater.py', '.'),
    ('models', 'models'),
]

# Templates et fichiers statiques
web_files = [
    ('templates', 'templates'),
    ('static', 'static'),
]

# Données des bibliothèques PDF (polices, ressources internes)
pdf_datas = collect_data_files('xhtml2pdf')
pdf_datas += collect_data_files('reportlab')

# Combiner toutes les données
datas = app_files + web_files + pdf_datas

# Ajouter les fichiers optionnels s'ils existent
optional_files = [
    ('etatdeslieux.pdf', '.'),
    ('uploads', 'uploads'),
]

for src, dst in optional_files:
    src_path = os.path.join(BASE_PATH, src)
    if os.path.exists(src_path):
        datas.append((src, dst))

# ========== HIDDEN IMPORTS ==========

hiddenimports = []

hiddenimports += collect_submodules('flask')
hiddenimports += collect_submodules('flask_sqlalchemy')
hiddenimports += collect_submodules('flask_login')
hiddenimports += collect_submodules('flask_bcrypt')
hiddenimports += collect_submodules('werkzeug')
hiddenimports += collect_submodules('jinja2')

hiddenimports += collect_submodules('sqlalchemy')
hiddenimports += [
    'sqlalchemy.sql.default_comparator',
    'sqlalchemy.dialects.mysql',
    'sqlalchemy.dialects.sqlite',
    'sqlalchemy.ext.declarative',
]

hiddenimports += [
    'markupsafe',
    'itsdangerous',
    'click',
    'blinker',
    'dotenv',
    'fitz',
    'pymupdf',
    'pymysql',
    'cryptography',
]

hiddenimports += [
    'urllib.request',
    'urllib.error',
    'zipfile',
    'tempfile',
    'hashlib',
]

hiddenimports += [
    'email',
    'email.mime',
    'email.mime.text',
    'email.mime.multipart',
    'email.mime.application',
    'smtplib',
    'decimal',
    'datetime',
    'json',
    're',
    'html',
    'types',
    'threading',
    'webbrowser',
    'ctypes',
    'shutil',
    'subprocess',
]

# QR Code
hiddenimports += [
    'qrcode',
    'qrcode.main',
    'qrcode.image.base',
    'qrcode.image.pure',
    'qrcode.image.pil',
    'qrcode.constants',
    'qrcode.exceptions',
    'qrcode.util',
]

hiddenimports += collect_submodules('xhtml2pdf')
hiddenimports += collect_submodules('reportlab')
hiddenimports += [
    'reportlab.graphics.barcode',
    'reportlab.graphics.barcode.code39',
    'reportlab.graphics.barcode.code93',
    'reportlab.graphics.barcode.code128',
    'reportlab.graphics.barcode.usps',
    'reportlab.graphics.barcode.eanbc',
    'reportlab.graphics.barcode.qr',
    'reportlab.graphics.barcode.widgets',
    'html5lib',
    'PIL',
    'PIL.Image',
    'svglib',
    'lxml',
    'lxml.etree',
    'lxml.html',
]

hiddenimports += ['models', 'auto_updater']
# ========== ANALYSE ==========

a = Analysis(
    ['launcher.py'],
    pathex=[BASE_PATH],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'tkinter',
        'PyQt5',
        'PyQt6',
        'PySide2',
        'PySide6',
        'wx',
        'IPython',
        'notebook',
        'sphinx',
        'pytest',
        'unittest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# ========== PYZ ==========

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

# ========== EXE ==========

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BayBay',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Mettre False pour cacher la console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='door_logo.ico',
    version=None,
    uac_admin=False,
)

# ========== COLLECTION ==========

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='BayBay',
)
