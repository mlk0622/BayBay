#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bay Bay - Système d'Auto-Update
==========================================
Ce module gère les mises à jour automatiques de l'application.
Télécharge le Setup.exe depuis GitHub et lance la réinstallation.
Les données utilisateur dans %APPDATA%/BayBay sont préservées.
"""

import os
import sys
import json
import tempfile
import threading
import subprocess
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# ========== CONFIGURATION ==========

# URL du serveur de mise à jour GitHub (liste des releases, pas /latest qui peut retourner 404)
UPDATE_SERVER_URL = "https://api.github.com/repos/mlk0622/BayBay/releases"

# Version actuelle de l'application
CURRENT_VERSION = "2.3.3.4"

# Fichier de configuration local
CONFIG_FILE = "update_config.json"

# Nom de l'application pour la recherche du désinstallateur
APP_NAME = "Bay Bay"


class AutoUpdater:
    """Gestionnaire de mises à jour automatiques via Setup.exe"""

    def __init__(self, current_version=CURRENT_VERSION, server_url=UPDATE_SERVER_URL):
        self.current_version = current_version
        self.server_url = server_url
        self.base_path = self._get_base_path()
        self.config = self._load_config()
        self.update_status = {
            'checking': False,
            'downloading': False,
            'installing': False,
            'progress': 0,
            'error': None,
            'message': ''
        }

    def _get_base_path(self):
        """Retourne le chemin de base de l'application"""
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.abspath(__file__))

    def _get_user_data_dir(self):
        """Retourne le chemin des données utilisateur (préservées lors de la mise à jour)"""
        if sys.platform == 'win32':
            appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
            return os.path.join(appdata, 'BayBay')
        return os.path.join(os.path.expanduser('~'), '.baybay')

    def _load_config(self):
        """Charge la configuration locale depuis le dossier utilisateur"""
        # Stocker la config dans le dossier utilisateur pour la préserver
        user_data = self._get_user_data_dir()
        config_path = os.path.join(user_data, CONFIG_FILE)
        default_config = {
            "auto_check": True,
            "check_interval_hours": 24,
            "last_check": None,
            "skip_version": None,
            "update_channel": "stable"
        }

        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    return {**default_config, **json.load(f)}
        except Exception:
            pass

        return default_config

    def _save_config(self):
        """Sauvegarde la configuration locale dans le dossier utilisateur"""
        user_data = self._get_user_data_dir()
        os.makedirs(user_data, exist_ok=True)
        config_path = os.path.join(user_data, CONFIG_FILE)
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Erreur sauvegarde config: {e}")

    def _version_tuple(self, version_str):
        """Convertit une version string en tuple comparable (supporte jusqu'a 4 chiffres)"""
        try:
            # Enlever le 'v' si présent
            version_str = str(version_str).lstrip('v')
            parts = version_str.split('.')
            # Prendre jusqu'a 4 parties (pour supporter X.X.X.X)
            result = []
            for p in parts[:4]:
                try:
                    result.append(int(p))
                except ValueError:
                    result.append(0)
            # Completer avec des zeros si moins de 4 parties
            while len(result) < 4:
                result.append(0)
            return tuple(result)
        except Exception:
            return (0, 0, 0, 0)

    def _is_newer_version(self, remote_version):
        """Vérifie si la version distante est plus récente"""
        current = self._version_tuple(self.current_version)
        remote = self._version_tuple(remote_version)
        print(f"[AutoUpdater] Comparaison: locale={self.current_version}{current} vs distante={remote_version}{remote}")
        print(f"[AutoUpdater] {remote} > {current} = {remote > current}")
        return remote > current

    def check_for_updates(self, silent=False):
        """
        Vérifie s'il y a une mise à jour disponible sur GitHub

        Args:
            silent: Si True, ne pas afficher de messages

        Returns:
            dict avec les infos de mise à jour ou None
        """
        self.update_status['checking'] = True
        self.update_status['error'] = None

        try:
            if not silent:
                print("[AutoUpdater] Verification des mises a jour sur GitHub...")

            # Requête vers l'API GitHub Releases
            headers = {
                'User-Agent': f'BayBay/{self.current_version}',
                'Accept': 'application/vnd.github.v3+json'
            }
            request = Request(self.server_url, headers=headers)

            with urlopen(request, timeout=15) as response:
                releases = json.loads(response.read().decode('utf-8'))

            # Trouver la première release non-draft et non-prerelease
            data = None
            if isinstance(releases, list):
                for release in releases:
                    if not release.get('draft', False) and not release.get('prerelease', False):
                        data = release
                        break
                # Si aucune release stable, prendre la première
                if not data and releases:
                    data = releases[0]
            elif isinstance(releases, dict):
                # Si c'est directement un objet (ancien format /latest)
                data = releases

            if not data:
                if not silent:
                    print("[AutoUpdater] Aucune release trouvee")
                self.update_status['checking'] = False
                return None

            # Parser la réponse GitHub Releases
            if 'tag_name' in data:
                remote_version = data['tag_name']
                download_url = None
                release_notes = data.get('body', '')
                asset_name = None

                if not silent:
                    print(f"[AutoUpdater] Release trouvee: {remote_version}")

                # Chercher le fichier Setup.exe dans les assets
                # Formats supportés: "Bay Bay Setup X.X.X.exe", "Bay.Bay.Setup.X.X.X.exe", etc.
                for asset in data.get('assets', []):
                    name = asset['name'].lower()
                    # Fichier .exe contenant "setup" ou "install"
                    if name.endswith('.exe') and ('setup' in name or 'install' in name):
                        download_url = asset['browser_download_url']
                        asset_name = asset['name']
                        if not silent:
                            print(f"[AutoUpdater] Asset Setup trouve: {asset['name']}")
                        break

                # Si pas de setup explicite, chercher un .exe contenant "baybay" ou "bay.bay"
                if not download_url:
                    for asset in data.get('assets', []):
                        name = asset['name'].lower()
                        if name.endswith('.exe') and ('baybay' in name or 'bay.bay' in name or 'bay bay' in name):
                            download_url = asset['browser_download_url']
                            asset_name = asset['name']
                            if not silent:
                                print(f"[AutoUpdater] Asset BayBay exe trouve: {asset['name']}")
                            break

                # En dernier recours, prendre le premier .exe
                if not download_url:
                    for asset in data.get('assets', []):
                        if asset['name'].lower().endswith('.exe'):
                            download_url = asset['browser_download_url']
                            asset_name = asset['name']
                            if not silent:
                                print(f"[AutoUpdater] Asset exe trouve: {asset['name']}")
                            break

                is_newer = self._is_newer_version(remote_version)

                update_info = {
                    'version': remote_version,
                    'download_url': download_url,
                    'asset_name': asset_name,
                    'release_notes': release_notes,
                    'published_at': data.get('published_at'),
                    'is_newer': is_newer,
                    'current_version': self.current_version
                }

                # Mettre à jour la date de vérification
                self.config['last_check'] = datetime.now().isoformat()
                self._save_config()

                if not silent:
                    if is_newer:
                        print(f"[AutoUpdater] Mise a jour disponible: {remote_version} (actuelle: {self.current_version})")
                    else:
                        print(f"[AutoUpdater] Application a jour (v{self.current_version})")

                self.update_status['checking'] = False
                return update_info

            self.update_status['checking'] = False
            return None

        except HTTPError as e:
            error_msg = f"Erreur HTTP: {e.code}"
            if not silent:
                print(f"[AutoUpdater] {error_msg}")
            self.update_status['error'] = error_msg
            self.update_status['checking'] = False
            return None
        except URLError as e:
            error_msg = f"Erreur reseau: {e.reason}"
            if not silent:
                print(f"[AutoUpdater] {error_msg}")
            self.update_status['error'] = error_msg
            self.update_status['checking'] = False
            return None
        except Exception as e:
            error_msg = f"Erreur: {e}"
            if not silent:
                print(f"[AutoUpdater] {error_msg}")
            self.update_status['error'] = error_msg
            self.update_status['checking'] = False
            return None

    def download_setup(self, download_url, asset_name=None, progress_callback=None):
        """
        Télécharge le Setup.exe depuis GitHub

        Args:
            download_url: URL du fichier Setup.exe
            asset_name: Nom du fichier (optionnel)
            progress_callback: Fonction callback(downloaded, total) pour la progression

        Returns:
            Chemin du fichier téléchargé ou None
        """
        self.update_status['downloading'] = True
        self.update_status['progress'] = 0
        self.update_status['message'] = 'Téléchargement en cours...'

        try:
            print(f"📥 Téléchargement du Setup depuis GitHub...")
            print(f"   URL: {download_url}")

            # Créer un dossier temporaire pour le téléchargement
            temp_dir = tempfile.mkdtemp(prefix='baybay_update_')
            filename = asset_name or 'BayBay_Setup.exe'
            setup_path = os.path.join(temp_dir, filename)

            headers = {'User-Agent': f'BayBay/{self.current_version}'}
            request = Request(download_url, headers=headers)

            with urlopen(request, timeout=120) as response:
                total_size = int(response.headers.get('Content-Length', 0))
                downloaded = 0
                chunk_size = 65536  # 64KB chunks pour plus de rapidité

                with open(setup_path, 'wb') as f:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)

                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            self.update_status['progress'] = percent

                            if progress_callback:
                                progress_callback(downloaded, total_size)
                            else:
                                print(f"\r   Progression: {percent:.1f}% ({downloaded // 1024 // 1024}MB / {total_size // 1024 // 1024}MB)", end='', flush=True)

            print(f"\n✅ Téléchargement terminé: {setup_path}")
            self.update_status['downloading'] = False
            self.update_status['progress'] = 100
            return setup_path

        except Exception as e:
            error_msg = f"Erreur de téléchargement: {e}"
            print(f"\n❌ {error_msg}")
            self.update_status['error'] = error_msg
            self.update_status['downloading'] = False
            return None

    def create_update_script(self, setup_path, silent_install=True):
        """
        Crée un script batch qui:
        1. Attend la fermeture de l'application
        2. Lance le nouveau Setup.exe (mode silencieux ou interactif)
        3. Nettoie les fichiers temporaires

        Args:
            setup_path: Chemin du Setup.exe téléchargé
            silent_install: Si True, installation silencieuse

        Returns:
            Chemin du script batch ou None
        """
        try:
            print("📦 Préparation de la mise à jour...")

            # Créer le script dans le dossier temp
            script_dir = os.path.dirname(setup_path)
            update_script = os.path.join(script_dir, '_baybay_update.bat')

            # Options NSIS pour installation silencieuse
            # /S = silencieux
            nsis_args = "/S" if silent_install else ""

            with open(update_script, 'w', encoding='utf-8') as f:
                f.write('@echo off\n')
                f.write('chcp 65001 >nul 2>&1\n')
                f.write('title Mise à jour Bay Bay\n')
                f.write('echo.\n')
                f.write('echo ========================================\n')
                f.write('echo    Mise à jour de Bay Bay en cours\n')
                f.write('echo ========================================\n')
                f.write('echo.\n')
                f.write('echo Fermeture de l\'application...\n')
                f.write('echo.\n')

                # Attendre que l'application se ferme (max 30 secondes)
                f.write('set /a count=0\n')
                f.write(':waitloop\n')
                f.write('tasklist /FI "IMAGENAME eq BayBay.exe" 2>NUL | find /I /N "BayBay.exe">NUL\n')
                f.write('if "%ERRORLEVEL%"=="0" (\n')
                f.write('    set /a count+=1\n')
                f.write('    if %count% GEQ 30 (\n')
                f.write('        echo Timeout - Fermeture forcee...\n')
                f.write('        taskkill /F /IM BayBay.exe >nul 2>&1\n')
                f.write('        timeout /t 2 /nobreak >nul\n')
                f.write('    ) else (\n')
                f.write('        timeout /t 1 /nobreak >nul\n')
                f.write('        goto waitloop\n')
                f.write('    )\n')
                f.write(')\n')
                f.write('echo.\n')

                # Fermer aussi Electron si lancé
                f.write('taskkill /F /IM "Bay Bay.exe" >nul 2>&1\n')
                f.write('timeout /t 2 /nobreak >nul\n')

                # Lancer le nouveau Setup
                f.write('echo Installation de la nouvelle version...\n')
                f.write('echo.\n')
                f.write(f'start /wait "" "{setup_path}" {nsis_args}\n')
                f.write('echo.\n')

                # Nettoyer
                f.write('echo Nettoyage...\n')
                f.write(f'rmdir /s /q "{script_dir}" >nul 2>&1\n')
                f.write('echo.\n')
                f.write('echo ========================================\n')
                f.write('echo    Mise à jour terminée!\n')
                f.write('echo ========================================\n')
                f.write('echo.\n')
                f.write('timeout /t 3 /nobreak >nul\n')
                f.write('exit\n')

            print(f"✅ Script de mise à jour créé: {update_script}")
            return update_script

        except Exception as e:
            print(f"❌ Erreur création script: {e}")
            self.update_status['error'] = str(e)
            return None

    def perform_update(self, silent_install=True, progress_callback=None):
        """
        Effectue le processus complet de mise à jour:
        1. Vérifie les mises à jour
        2. Télécharge le Setup.exe
        3. Crée et lance le script de mise à jour
        4. Quitte l'application

        Args:
            silent_install: Si True, installation silencieuse
            progress_callback: Callback pour la progression

        Returns:
            True si mise à jour lancée, False sinon
        """
        self.update_status['installing'] = True
        self.update_status['message'] = 'Vérification des mises à jour...'

        # Vérifier les mises à jour
        update_info = self.check_for_updates()

        if not update_info:
            self.update_status['installing'] = False
            self.update_status['error'] = 'Impossible de vérifier les mises à jour'
            return False

        if not update_info.get('is_newer'):
            print(f"✅ Vous avez la dernière version ({self.current_version})")
            self.update_status['installing'] = False
            self.update_status['message'] = 'Application à jour'
            return False

        # Afficher les infos
        print(f"\n📋 Nouvelle version disponible: {update_info['version']}")
        print(f"   Version actuelle: {self.current_version}")
        if update_info.get('release_notes'):
            print(f"\n📝 Notes de version:")
            print("-" * 40)
            print(update_info['release_notes'][:500])
            print("-" * 40)

        # Vérifier qu'il y a une URL de téléchargement
        download_url = update_info.get('download_url')
        if not download_url:
            error = "Aucun fichier Setup.exe disponible dans cette release"
            print(f"❌ {error}")
            self.update_status['error'] = error
            self.update_status['installing'] = False
            return False

        # Télécharger le Setup
        self.update_status['message'] = 'Téléchargement en cours...'
        setup_path = self.download_setup(
            download_url,
            update_info.get('asset_name'),
            progress_callback
        )

        if not setup_path:
            self.update_status['installing'] = False
            return False

        # Créer le script de mise à jour
        self.update_status['message'] = 'Préparation de l\'installation...'
        update_script = self.create_update_script(setup_path, silent_install)

        if not update_script:
            self.update_status['installing'] = False
            return False

        # Lancer le script et quitter
        print("\n🚀 Lancement de la mise à jour...")
        print("   L'application va se fermer et se réinstaller automatiquement.")
        print("   Vos données seront conservées.\n")

        self.update_status['message'] = 'Lancement de l\'installation...'

        # Lancer le script en mode détaché
        subprocess.Popen(
            update_script,
            shell=True,
            creationflags=subprocess.CREATE_NEW_CONSOLE | subprocess.DETACHED_PROCESS
        )

        # Quitter l'application
        sys.exit(0)


def check_updates_async(callback=None):
    """Vérifie les mises à jour de manière asynchrone"""
    def _check():
        updater = AutoUpdater()
        result = updater.check_for_updates(silent=True)
        if callback:
            callback(result)

    thread = threading.Thread(target=_check, daemon=True)
    thread.start()
    return thread


# ========== INTERFACE FLASK ==========

def register_update_routes(app):
    """Enregistre les routes de mise à jour dans l'application Flask"""
    from flask import jsonify, request

    @app.route('/api/updates/check')
    def api_check_updates():
        """API pour vérifier les mises à jour"""
        print(f"[API] /api/updates/check appelé")
        print(f"[API] CURRENT_VERSION = {CURRENT_VERSION}")

        updater = AutoUpdater()
        print(f"[API] updater.current_version = {updater.current_version}")

        result = updater.check_for_updates(silent=False)  # Mettre silent=False pour voir les logs

        if result:
            print(f"[API] Resultat: version={result.get('version')}, is_newer={result.get('is_newer')}")
            return jsonify({
                'available': result.get('is_newer', False),
                'version': result.get('version'),
                'current_version': result.get('current_version', CURRENT_VERSION),
                'release_notes': result.get('release_notes'),
                'download_url': result.get('download_url'),
                'asset_name': result.get('asset_name')
            })

        print(f"[API] Erreur: aucun resultat")
        return jsonify({
            'available': False,
            'current_version': CURRENT_VERSION,
            'error': 'Impossible de verifier les mises a jour'
        })

    @app.route('/api/updates/download', methods=['POST'])
    def api_download_update():
        """API pour télécharger et installer une mise à jour"""
        updater = AutoUpdater()
        update_info = updater.check_for_updates(silent=True)

        if not update_info or not update_info.get('is_newer'):
            return jsonify({'success': False, 'message': 'Aucune mise à jour disponible'})

        download_url = update_info.get('download_url')
        if not download_url:
            return jsonify({'success': False, 'message': 'Aucun fichier Setup.exe disponible'})

        # Récupérer les options
        data = request.get_json() or {}
        silent_install = data.get('silent', True)

        # Lancer la mise à jour dans un thread
        def do_update():
            updater.perform_update(silent_install=silent_install)

        thread = threading.Thread(target=do_update, daemon=True)
        thread.start()

        return jsonify({
            'success': True,
            'message': 'Mise à jour en cours, l\'application va redémarrer',
            'version': update_info.get('version')
        })

    @app.route('/api/updates/config', methods=['GET', 'POST'])
    def api_update_config():
        """API pour configurer les mises à jour automatiques"""
        updater = AutoUpdater()

        if request.method == 'POST':
            data = request.get_json() or {}
            if 'auto_check' in data:
                updater.config['auto_check'] = bool(data['auto_check'])
            if 'check_interval_hours' in data:
                updater.config['check_interval_hours'] = int(data['check_interval_hours'])
            updater._save_config()

        return jsonify(updater.config)

    @app.route('/api/updates/status')
    def api_update_status():
        """API pour obtenir le statut de la mise à jour en cours"""
        updater = AutoUpdater()
        return jsonify(updater.update_status)


# ========== TESTS ==========

if __name__ == '__main__':
    print(f"Version actuelle: {CURRENT_VERSION}")
    print("-" * 40)

    updater = AutoUpdater()

    # Test de vérification
    result = updater.check_for_updates()

    if result:
        print(f"\nVersion distante: {result.get('version')}")
        print(f"Mise à jour disponible: {result.get('is_newer')}")
        print(f"URL de téléchargement: {result.get('download_url')}")
        print(f"Nom du fichier: {result.get('asset_name')}")
    else:
        print("\nImpossible de vérifier les mises à jour")
