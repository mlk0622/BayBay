#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bay Bay - Système d'Auto-Update
==========================================
Ce module gère les mises à jour automatiques de l'application.
"""

import os
import sys
import json
import shutil
import tempfile
import threading
import hashlib
import zipfile
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# ========== CONFIGURATION ==========

# URL du serveur de mise à jour GitHub
UPDATE_SERVER_URL = "https://api.github.com/repos/mlk0622/BayBay/releases/latest"

# Version actuelle de l'application
CURRENT_VERSION = "2.2.9"

# Fichier de configuration local
CONFIG_FILE = "update_config.json"


class AutoUpdater:
    """Gestionnaire de mises à jour automatiques"""

    def __init__(self, current_version=CURRENT_VERSION, server_url=UPDATE_SERVER_URL):
        self.current_version = current_version
        self.server_url = server_url
        self.base_path = self._get_base_path()
        self.config = self._load_config()

    def _get_base_path(self):
        """Retourne le chemin de base de l'application"""
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.abspath(__file__))

    def _load_config(self):
        """Charge la configuration locale"""
        config_path = os.path.join(self.base_path, "data", CONFIG_FILE)
        default_config = {
            "auto_check": True,
            "check_interval_hours": 24,
            "last_check": None,
            "skip_version": None,
            "update_channel": "stable"  # stable, beta
        }

        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    return {**default_config, **json.load(f)}
        except Exception:
            pass

        return default_config

    def _save_config(self):
        """Sauvegarde la configuration locale"""
        config_path = os.path.join(self.base_path, "data", CONFIG_FILE)
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Erreur sauvegarde config: {e}")

    def _version_tuple(self, version_str):
        """Convertit une version string en tuple comparable"""
        try:
            # Enlever le 'v' si présent
            version_str = version_str.lstrip('v')
            parts = version_str.split('.')
            return tuple(int(p) for p in parts[:3])
        except Exception:
            return (0, 0, 0)

    def _is_newer_version(self, remote_version):
        """Vérifie si la version distante est plus récente"""
        current = self._version_tuple(self.current_version)
        remote = self._version_tuple(remote_version)
        return remote > current

    def check_for_updates(self, silent=False):
        """
        Vérifie s'il y a une mise à jour disponible

        Args:
            silent: Si True, ne pas afficher de messages

        Returns:
            dict avec les infos de mise à jour ou None
        """
        try:
            if not silent:
                print("🔍 Vérification des mises à jour...")

            # Requête vers le serveur
            headers = {
                'User-Agent': f'BayBay/{self.current_version}',
                'Accept': 'application/json'
            }
            request = Request(self.server_url, headers=headers)

            with urlopen(request, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))

            # Parser la réponse (format GitHub Releases)
            if 'tag_name' in data:
                remote_version = data['tag_name']
                download_url = None
                release_notes = data.get('body', '')

                # Trouver l'asset Windows (zip)
                for asset in data.get('assets', []):
                    if asset['name'].endswith('.zip') and 'windows' in asset['name'].lower():
                        download_url = asset['browser_download_url']
                        break

                # Si pas trouvé, prendre le premier zip
                if not download_url:
                    for asset in data.get('assets', []):
                        if asset['name'].endswith('.zip'):
                            download_url = asset['browser_download_url']
                            break

                update_info = {
                    'version': remote_version,
                    'download_url': download_url,
                    'release_notes': release_notes,
                    'published_at': data.get('published_at'),
                    'is_newer': self._is_newer_version(remote_version)
                }

                # Mettre à jour la date de vérification
                self.config['last_check'] = datetime.now().isoformat()
                self._save_config()

                if update_info['is_newer'] and not silent:
                    print(f"✅ Mise à jour disponible: v{remote_version}")

                return update_info

            return None

        except HTTPError as e:
            if not silent:
                print(f"❌ Erreur HTTP: {e.code}")
            return None
        except URLError as e:
            if not silent:
                print(f"❌ Erreur réseau: {e.reason}")
            return None
        except Exception as e:
            if not silent:
                print(f"❌ Erreur: {e}")
            return None

    def download_update(self, download_url, progress_callback=None):
        """
        Télécharge la mise à jour

        Args:
            download_url: URL du fichier à télécharger
            progress_callback: Fonction callback(downloaded, total) pour afficher la progression

        Returns:
            Chemin du fichier téléchargé ou None
        """
        try:
            print(f"📥 Téléchargement de la mise à jour...")

            # Créer un fichier temporaire
            temp_dir = tempfile.mkdtemp(prefix='baybay_update_')
            zip_path = os.path.join(temp_dir, 'update.zip')

            headers = {'User-Agent': f'BayBay/{self.current_version}'}
            request = Request(download_url, headers=headers)

            with urlopen(request, timeout=60) as response:
                total_size = int(response.headers.get('Content-Length', 0))
                downloaded = 0
                chunk_size = 8192

                with open(zip_path, 'wb') as f:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)

                        if progress_callback and total_size > 0:
                            progress_callback(downloaded, total_size)
                        elif total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\r   Progression: {percent:.1f}%", end='', flush=True)

            print("\n✅ Téléchargement terminé")
            return zip_path

        except Exception as e:
            print(f"\n❌ Erreur de téléchargement: {e}")
            return None

    def install_update(self, zip_path):
        """
        Installe la mise à jour

        Args:
            zip_path: Chemin du fichier zip téléchargé

        Returns:
            True si succès, False sinon
        """
        try:
            print("📦 Installation de la mise à jour...")

            # Créer un dossier de backup
            backup_dir = os.path.join(self.base_path, '_backup_' + datetime.now().strftime('%Y%m%d_%H%M%S'))

            # Extraire le zip
            temp_extract = os.path.join(os.path.dirname(zip_path), 'extracted')
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_extract)

            # Trouver le dossier racine dans l'extraction
            extracted_items = os.listdir(temp_extract)
            if len(extracted_items) == 1 and os.path.isdir(os.path.join(temp_extract, extracted_items[0])):
                source_dir = os.path.join(temp_extract, extracted_items[0])
            else:
                source_dir = temp_extract

            # Créer le script de mise à jour qui s'exécutera après fermeture
            update_script = os.path.join(self.base_path, '_update.bat')
            with open(update_script, 'w', encoding='utf-8') as f:
                f.write('@echo off\n')
                f.write('chcp 65001 >nul 2>&1\n')
                f.write('title Mise à jour - Bay Bay\n')
                f.write('echo.\n')
                f.write('echo Mise à jour en cours, veuillez patienter...\n')
                f.write('timeout /t 2 /nobreak >nul\n')
                f.write(f'xcopy /s /e /y "{source_dir}\\*" "{self.base_path}\\" >nul 2>&1\n')
                f.write('echo.\n')
                f.write('echo Mise à jour terminée!\n')
                f.write(f'start "" "{os.path.join(self.base_path, "BayBay.exe")}"\n')
                f.write(f'del /f /q "{update_script}"\n')
                f.write(f'rmdir /s /q "{os.path.dirname(zip_path)}"\n')

            print("✅ Mise à jour préparée")
            print("🔄 L'application va redémarrer...")

            return update_script

        except Exception as e:
            print(f"❌ Erreur d'installation: {e}")
            return None

    def perform_update(self):
        """Effectue le processus complet de mise à jour"""
        # Vérifier les mises à jour
        update_info = self.check_for_updates()

        if not update_info or not update_info.get('is_newer'):
            print("✅ Vous avez la dernière version")
            return False

        # Afficher les infos
        print(f"\n📋 Notes de version {update_info['version']}:")
        print("-" * 40)
        print(update_info.get('release_notes', 'Pas de notes disponibles')[:500])
        print("-" * 40)

        # Télécharger
        download_url = update_info.get('download_url')
        if not download_url:
            print("❌ Aucun fichier de téléchargement disponible")
            return False

        zip_path = self.download_update(download_url)
        if not zip_path:
            return False

        # Installer
        update_script = self.install_update(zip_path)
        if not update_script:
            return False

        # Lancer le script de mise à jour et quitter
        import subprocess
        subprocess.Popen(update_script, shell=True)
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
        updater = AutoUpdater()
        result = updater.check_for_updates(silent=True)
        if result:
            return jsonify({
                'available': result.get('is_newer', False),
                'version': result.get('version'),
                'release_notes': result.get('release_notes'),
                'current_version': CURRENT_VERSION
            })
        return jsonify({
            'available': False,
            'current_version': CURRENT_VERSION
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
            return jsonify({'success': False, 'message': 'URL de téléchargement non disponible'})

        # Lancer la mise à jour dans un thread
        def do_update():
            updater.perform_update()

        thread = threading.Thread(target=do_update, daemon=True)
        thread.start()

        return jsonify({
            'success': True,
            'message': 'Mise à jour en cours, l\'application va redémarrer'
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
    else:
        print("\nImpossible de vérifier les mises à jour")
        print("(Configurez UPDATE_SERVER_URL avec votre serveur)")
