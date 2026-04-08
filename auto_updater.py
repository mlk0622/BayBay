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
import traceback
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# ========== CONFIGURATION ==========

# URL du serveur de mise à jour GitHub (liste des releases, pas /latest qui peut retourner 404)
UPDATE_SERVER_URL = "https://api.github.com/repos/mlk0622/BayBay/releases"

# Version actuelle de l'application
CURRENT_VERSION = "2.2.3.7"

# Fichier de configuration local
CONFIG_FILE = "update_config.json"

# Nom de l'application pour la recherche du désinstallateur
APP_NAME = "Bay Bay"

# Fichier de log pour le debug
LOG_FILE = "updater_debug.log"


def get_log_path():
    """Retourne le chemin du fichier de log dans %APPDATA%/BayBay"""
    if sys.platform == 'win32':
        appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
        log_dir = os.path.join(appdata, 'BayBay')
    else:
        log_dir = os.path.join(os.path.expanduser('~'), '.baybay')

    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, LOG_FILE)


def log_debug(message):
    """Ecrit un message dans le fichier de log et dans la console"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] {message}"

    # Afficher dans la console
    print(log_line)

    # Ecrire dans le fichier de log
    try:
        log_path = get_log_path()
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(log_line + "\n")
    except Exception as e:
        print(f"Erreur ecriture log: {e}")


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
            log_debug(f"Erreur sauvegarde config: {e}")

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
        log_debug(f"[AutoUpdater] Comparaison: locale={self.current_version}{current} vs distante={remote_version}{remote}")
        log_debug(f"[AutoUpdater] {remote} > {current} = {remote > current}")
        return remote > current

    def check_for_updates(self, silent=False):
        """
        Vérifie s'il y a une mise à jour disponible sur GitHub

        Args:
            silent: Si True, ne pas afficher de messages

        Returns:
            dict avec les infos de mise à jour ou None
        """
        log_debug(f"[AutoUpdater] === DEBUT check_for_updates (silent={silent}) ===")
        log_debug(f"[AutoUpdater] Version actuelle: {self.current_version}")
        log_debug(f"[AutoUpdater] URL: {self.server_url}")

        self.update_status['checking'] = True
        self.update_status['error'] = None

        try:
            log_debug("[AutoUpdater] Verification des mises a jour sur GitHub...")

            # Requête vers l'API GitHub Releases
            headers = {
                'User-Agent': f'BayBay/{self.current_version}',
                'Accept': 'application/vnd.github.v3+json'
            }
            request = Request(self.server_url, headers=headers)
            log_debug(f"[AutoUpdater] Headers: {headers}")

            with urlopen(request, timeout=15) as response:
                log_debug(f"[AutoUpdater] HTTP Status: {response.status}")
                releases = json.loads(response.read().decode('utf-8'))
                log_debug(f"[AutoUpdater] Nombre de releases: {len(releases) if isinstance(releases, list) else 1}")

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
                log_debug("[AutoUpdater] ERREUR: Aucune release trouvee")
                self.update_status['checking'] = False
                return None

            # Parser la réponse GitHub Releases
            if 'tag_name' in data:
                remote_version = data['tag_name']
                download_url = None
                release_notes = data.get('body', '')
                asset_name = None

                log_debug(f"[AutoUpdater] Release trouvee: {remote_version}")
                log_debug(f"[AutoUpdater] Assets disponibles: {[a['name'] for a in data.get('assets', [])]}")

                # Chercher le fichier Setup.exe dans les assets
                # Formats supportés: "Bay Bay Setup X.X.X.exe", "Bay.Bay.Setup.X.X.X.exe", etc.
                for asset in data.get('assets', []):
                    name = asset['name'].lower()
                    # Fichier .exe contenant "setup" ou "install"
                    if name.endswith('.exe') and ('setup' in name or 'install' in name):
                        download_url = asset['browser_download_url']
                        asset_name = asset['name']
                        log_debug(f"[AutoUpdater] Asset Setup trouve: {asset['name']}")
                        break

                # Si pas de setup explicite, chercher un .exe contenant "baybay" ou "bay.bay"
                if not download_url:
                    for asset in data.get('assets', []):
                        name = asset['name'].lower()
                        if name.endswith('.exe') and ('baybay' in name or 'bay.bay' in name or 'bay bay' in name):
                            download_url = asset['browser_download_url']
                            asset_name = asset['name']
                            log_debug(f"[AutoUpdater] Asset BayBay exe trouve: {asset['name']}")
                            break

                # En dernier recours, prendre le premier .exe
                if not download_url:
                    for asset in data.get('assets', []):
                        if asset['name'].lower().endswith('.exe'):
                            download_url = asset['browser_download_url']
                            asset_name = asset['name']
                            log_debug(f"[AutoUpdater] Asset exe trouve: {asset['name']}")
                            break

                if not download_url:
                    log_debug("[AutoUpdater] ERREUR: Aucun fichier .exe trouve dans les assets!")

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

                log_debug(f"[AutoUpdater] Resultat: is_newer={is_newer}, download_url={download_url}")

                # Mettre à jour la date de vérification
                self.config['last_check'] = datetime.now().isoformat()
                self._save_config()

                if is_newer:
                    log_debug(f"[AutoUpdater] >>> MISE A JOUR DISPONIBLE: {remote_version} (actuelle: {self.current_version})")
                else:
                    log_debug(f"[AutoUpdater] Application a jour (v{self.current_version})")

                log_debug(f"[AutoUpdater] === FIN check_for_updates ===")
                self.update_status['checking'] = False
                return update_info

            log_debug("[AutoUpdater] ERREUR: Pas de tag_name dans la release")
            self.update_status['checking'] = False
            return None

        except HTTPError as e:
            error_msg = f"Erreur HTTP: {e.code}"
            log_debug(f"[AutoUpdater] {error_msg}")
            log_debug(f"[AutoUpdater] Traceback: {traceback.format_exc()}")
            self.update_status['error'] = error_msg
            self.update_status['checking'] = False
            return None
        except URLError as e:
            error_msg = f"Erreur reseau: {e.reason}"
            log_debug(f"[AutoUpdater] {error_msg}")
            log_debug(f"[AutoUpdater] Traceback: {traceback.format_exc()}")
            self.update_status['error'] = error_msg
            self.update_status['checking'] = False
            return None
        except Exception as e:
            error_msg = f"Erreur: {e}"
            log_debug(f"[AutoUpdater] {error_msg}")
            log_debug(f"[AutoUpdater] Traceback: {traceback.format_exc()}")
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
        log_debug(f"[AutoUpdater] === DEBUT download_setup ===")
        log_debug(f"[AutoUpdater] URL: {download_url}")
        log_debug(f"[AutoUpdater] Asset: {asset_name}")

        self.update_status['downloading'] = True
        self.update_status['progress'] = 0
        self.update_status['message'] = 'Telechargement en cours...'

        try:
            # Créer un dossier temporaire pour le téléchargement
            temp_dir = tempfile.mkdtemp(prefix='baybay_update_')
            filename = asset_name or 'BayBay_Setup.exe'
            setup_path = os.path.join(temp_dir, filename)
            log_debug(f"[AutoUpdater] Chemin de telechargement: {setup_path}")

            headers = {'User-Agent': f'BayBay/{self.current_version}'}
            request = Request(download_url, headers=headers)

            with urlopen(request, timeout=300) as response:  # 5 min timeout pour gros fichiers
                total_size = int(response.headers.get('Content-Length', 0))
                log_debug(f"[AutoUpdater] Taille totale: {total_size / 1024 / 1024:.2f} MB")
                downloaded = 0
                chunk_size = 131072  # 128KB chunks pour plus de rapidité
                last_log_percent = 0

                with open(setup_path, 'wb') as f:
                    while True:
                        try:
                            chunk = response.read(chunk_size)
                        except Exception as e:
                            log_debug(f"[AutoUpdater] Erreur lecture chunk: {e}")
                            raise

                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)

                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            self.update_status['progress'] = percent

                            # Logger tous les 10%
                            if int(percent / 10) > int(last_log_percent / 10):
                                log_debug(f"[AutoUpdater] Telechargement: {percent:.1f}% ({downloaded / 1024 / 1024:.1f} / {total_size / 1024 / 1024:.1f} MB)")
                                last_log_percent = percent

                            if progress_callback:
                                progress_callback(downloaded, total_size)

            log_debug(f"[AutoUpdater] Telechargement termine: {setup_path}")
            log_debug(f"[AutoUpdater] Taille fichier: {os.path.getsize(setup_path)} bytes")
            self.update_status['downloading'] = False
            self.update_status['progress'] = 100
            return setup_path

        except Exception as e:
            error_msg = f"Erreur de telechargement: {e}"
            log_debug(f"[AutoUpdater] {error_msg}")
            log_debug(f"[AutoUpdater] Traceback: {traceback.format_exc()}")
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
        log_debug(f"[AutoUpdater] === DEBUT create_update_script ===")
        log_debug(f"[AutoUpdater] Setup path: {setup_path}")
        log_debug(f"[AutoUpdater] Silent install: {silent_install}")

        try:
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

            log_debug(f"[AutoUpdater] Script de mise a jour cree: {update_script}")
            return update_script

        except Exception as e:
            log_debug(f"[AutoUpdater] Erreur creation script: {e}")
            log_debug(f"[AutoUpdater] Traceback: {traceback.format_exc()}")
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
        log_debug(f"[AutoUpdater] === DEBUT perform_update ===")
        self.update_status['installing'] = True
        self.update_status['message'] = 'Verification des mises a jour...'

        # Vérifier les mises à jour
        update_info = self.check_for_updates()

        if not update_info:
            log_debug("[AutoUpdater] Erreur: pas d'update_info")
            self.update_status['installing'] = False
            self.update_status['error'] = 'Impossible de verifier les mises a jour'
            return False

        if not update_info.get('is_newer'):
            log_debug(f"[AutoUpdater] Pas de mise a jour (version actuelle: {self.current_version})")
            self.update_status['installing'] = False
            self.update_status['message'] = 'Application a jour'
            return False

        # Afficher les infos
        log_debug(f"[AutoUpdater] Nouvelle version disponible: {update_info['version']}")
        log_debug(f"[AutoUpdater] Version actuelle: {self.current_version}")

        # Vérifier qu'il y a une URL de téléchargement
        download_url = update_info.get('download_url')
        if not download_url:
            error = "Aucun fichier Setup.exe disponible dans cette release"
            log_debug(f"[AutoUpdater] ERREUR: {error}")
            self.update_status['error'] = error
            self.update_status['installing'] = False
            return False

        # Télécharger le Setup
        self.update_status['message'] = 'Telechargement en cours...'
        setup_path = self.download_setup(
            download_url,
            update_info.get('asset_name'),
            progress_callback
        )

        if not setup_path:
            log_debug("[AutoUpdater] Erreur: echec du telechargement")
            self.update_status['installing'] = False
            return False

        # Créer le script de mise à jour
        self.update_status['message'] = 'Preparation de l\'installation...'
        update_script = self.create_update_script(setup_path, silent_install)

        if not update_script:
            log_debug("[AutoUpdater] Erreur: echec creation script")
            self.update_status['installing'] = False
            return False

        # Lancer le script et quitter
        log_debug("[AutoUpdater] Lancement du script de mise a jour...")
        log_debug(f"[AutoUpdater] Script: {update_script}")

        self.update_status['message'] = 'Lancement de l\'installation...'

        # Lancer le script en mode détaché
        subprocess.Popen(
            update_script,
            shell=True,
            creationflags=subprocess.CREATE_NEW_CONSOLE | subprocess.DETACHED_PROCESS
        )

        log_debug("[AutoUpdater] Script lance, fermeture de l'application...")
        # Quitter l'application
        sys.exit(0)


def check_updates_async(callback=None):
    """Vérifie les mises à jour de manière asynchrone"""
    def _check():
        log_debug("[check_updates_async] Demarrage verification asynchrone")
        updater = AutoUpdater()
        result = updater.check_for_updates(silent=False)
        if callback:
            callback(result)

    thread = threading.Thread(target=_check, daemon=True)
    thread.start()
    return thread


# ========== INTERFACE FLASK ==========

def register_update_routes(app):
    """Enregistre les routes de mise à jour dans l'application Flask"""
    from flask import jsonify, request

    log_debug(f"[Flask] Enregistrement des routes de mise a jour")
    log_debug(f"[Flask] CURRENT_VERSION = {CURRENT_VERSION}")
    log_debug(f"[Flask] Fichier de log: {get_log_path()}")

    @app.route('/api/updates/check')
    def api_check_updates():
        """API pour vérifier les mises à jour"""
        log_debug(f"[API] === /api/updates/check appele ===")
        log_debug(f"[API] CURRENT_VERSION dans le module = {CURRENT_VERSION}")

        updater = AutoUpdater()
        log_debug(f"[API] updater.current_version = {updater.current_version}")

        result = updater.check_for_updates(silent=False)

        if result:
            log_debug(f"[API] Resultat: version={result.get('version')}, is_newer={result.get('is_newer')}")
            response = {
                'available': result.get('is_newer', False),
                'version': result.get('version'),
                'current_version': result.get('current_version', CURRENT_VERSION),
                'release_notes': result.get('release_notes'),
                'download_url': result.get('download_url'),
                'asset_name': result.get('asset_name')
            }
            log_debug(f"[API] Response: {response}")
            return jsonify(response)

        log_debug(f"[API] ERREUR: aucun resultat retourne")
        return jsonify({
            'available': False,
            'current_version': CURRENT_VERSION,
            'error': 'Impossible de verifier les mises a jour'
        })

    @app.route('/api/updates/download', methods=['POST'])
    def api_download_update():
        """API pour télécharger et installer une mise à jour"""
        log_debug(f"[API] === /api/updates/download appele ===")

        updater = AutoUpdater()
        update_info = updater.check_for_updates(silent=False)

        if not update_info or not update_info.get('is_newer'):
            log_debug("[API] Pas de mise a jour disponible")
            return jsonify({'success': False, 'message': 'Aucune mise a jour disponible'})

        download_url = update_info.get('download_url')
        if not download_url:
            log_debug("[API] Pas de download_url")
            return jsonify({'success': False, 'message': 'Aucun fichier Setup.exe disponible'})

        # Récupérer les options
        data = request.get_json() or {}
        silent_install = data.get('silent', True)
        log_debug(f"[API] silent_install = {silent_install}")

        # Lancer la mise à jour dans un thread NON-daemon pour qu'il survive
        def do_update():
            log_debug("[API] Thread de mise a jour demarre")
            try:
                updater.perform_update(silent_install=silent_install)
            except Exception as e:
                log_debug(f"[API] ERREUR dans thread update: {e}")
                log_debug(f"[API] Traceback: {traceback.format_exc()}")

        # IMPORTANT: daemon=False pour que le thread survive au retour de l'API
        thread = threading.Thread(target=do_update, daemon=False)
        thread.start()
        log_debug(f"[API] Thread demarre avec daemon=False")

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
