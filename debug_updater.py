#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug Auto-Updater - Script de diagnostic complet
==================================================
Execute ce script pour generer un rapport de debug complet
Le rapport sera sauvegarde dans debug_updater_report.txt
"""

import os
import sys
import json
import traceback
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# Fichier de sortie
REPORT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_updater_report.txt")

# Configuration
GITHUB_RELEASES_URL = "https://api.github.com/repos/mlk0622/BayBay/releases"
CURRENT_VERSION = "2.3.3.2"  # Version actuelle de l'app

def log(message, file_handle=None):
    """Affiche et ecrit dans le fichier"""
    print(message)
    if file_handle:
        file_handle.write(message + "\n")

def version_tuple(version_str):
    """Convertit une version string en tuple comparable"""
    try:
        # Enlever le 'v' si present
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
    except Exception as e:
        return (0, 0, 0, 0)

def is_newer_version(remote_version, current_version):
    """Verifie si la version distante est plus recente"""
    current = version_tuple(current_version)
    remote = version_tuple(remote_version)
    return remote > current

def run_debug():
    """Execute le diagnostic complet"""

    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        log("=" * 70, f)
        log("    DEBUG AUTO-UPDATER - RAPPORT COMPLET", f)
        log("=" * 70, f)
        log(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", f)
        log(f"Python: {sys.version}", f)
        log(f"OS: {sys.platform}", f)
        log("=" * 70, f)
        log("", f)

        # 1. Version actuelle
        log("[ETAPE 1] VERSION ACTUELLE", f)
        log("-" * 40, f)
        log(f"CURRENT_VERSION dans le code: {CURRENT_VERSION}", f)
        log(f"Version tuple: {version_tuple(CURRENT_VERSION)}", f)
        log("", f)

        # 2. Verifier auto_updater.py
        log("[ETAPE 2] VERIFICATION DE auto_updater.py", f)
        log("-" * 40, f)
        try:
            from auto_updater import CURRENT_VERSION as AUTO_UPDATER_VERSION
            log(f"Version dans auto_updater.py: {AUTO_UPDATER_VERSION}", f)
            if AUTO_UPDATER_VERSION != CURRENT_VERSION:
                log(f"ATTENTION: Les versions ne correspondent pas!", f)
        except Exception as e:
            log(f"ERREUR import auto_updater: {e}", f)
        log("", f)

        # 3. Requete GitHub API
        log("[ETAPE 3] REQUETE GITHUB API", f)
        log("-" * 40, f)
        log(f"URL: {GITHUB_RELEASES_URL}", f)

        releases = None
        try:
            headers = {
                'User-Agent': f'BayBay/{CURRENT_VERSION}',
                'Accept': 'application/vnd.github.v3+json'
            }
            req = Request(GITHUB_RELEASES_URL, headers=headers)
            log(f"Headers: {headers}", f)

            with urlopen(req, timeout=15) as response:
                status = response.status
                log(f"Status HTTP: {status}", f)
                raw_data = response.read().decode('utf-8')
                releases = json.loads(raw_data)
                log(f"Nombre de releases: {len(releases) if isinstance(releases, list) else 'N/A'}", f)

        except HTTPError as e:
            log(f"ERREUR HTTP: {e.code} - {e.reason}", f)
            log(f"Traceback: {traceback.format_exc()}", f)
        except URLError as e:
            log(f"ERREUR URL/Reseau: {e.reason}", f)
            log(f"Traceback: {traceback.format_exc()}", f)
        except Exception as e:
            log(f"ERREUR: {e}", f)
            log(f"Traceback: {traceback.format_exc()}", f)
        log("", f)

        # 4. Analyser les releases
        if releases:
            log("[ETAPE 4] ANALYSE DES RELEASES", f)
            log("-" * 40, f)

            for i, release in enumerate(releases[:5]):  # Top 5
                tag = release.get('tag_name', 'N/A')
                draft = release.get('draft', False)
                prerelease = release.get('prerelease', False)
                published = release.get('published_at', 'N/A')
                assets = release.get('assets', [])

                log(f"\nRelease #{i+1}:", f)
                log(f"  Tag: {tag}", f)
                log(f"  Version tuple: {version_tuple(tag)}", f)
                log(f"  Draft: {draft}", f)
                log(f"  Prerelease: {prerelease}", f)
                log(f"  Published: {published}", f)
                log(f"  Assets ({len(assets)}):", f)

                for asset in assets:
                    name = asset.get('name', 'N/A')
                    url = asset.get('browser_download_url', 'N/A')
                    size = asset.get('size', 0)
                    log(f"    - {name} ({size / 1024 / 1024:.2f} MB)", f)
                    log(f"      URL: {url}", f)
            log("", f)

        # 5. Trouver la latest release
        log("[ETAPE 5] RECHERCHE DE LA LATEST RELEASE", f)
        log("-" * 40, f)

        latest_release = None
        if releases and isinstance(releases, list):
            # Chercher la premiere release non-draft et non-prerelease
            for release in releases:
                if not release.get('draft', False) and not release.get('prerelease', False):
                    latest_release = release
                    break

            if not latest_release and releases:
                latest_release = releases[0]
                log("ATTENTION: Aucune release stable trouvee, utilisation de la premiere", f)

        if latest_release:
            latest_version = latest_release.get('tag_name', 'N/A')
            log(f"Latest release tag: {latest_version}", f)
            log(f"Latest version tuple: {version_tuple(latest_version)}", f)
        else:
            log("ERREUR: Aucune release trouvee!", f)
        log("", f)

        # 6. Comparaison de version
        log("[ETAPE 6] COMPARAISON DE VERSION", f)
        log("-" * 40, f)

        if latest_release:
            latest_version = latest_release.get('tag_name', '0.0.0')

            current_tuple = version_tuple(CURRENT_VERSION)
            latest_tuple = version_tuple(latest_version)

            log(f"Version actuelle: {CURRENT_VERSION} -> {current_tuple}", f)
            log(f"Version distante: {latest_version} -> {latest_tuple}", f)
            log(f"", f)
            log(f"Comparaison: {latest_tuple} > {current_tuple} ?", f)

            is_newer = is_newer_version(latest_version, CURRENT_VERSION)
            log(f"Resultat: {is_newer}", f)

            if is_newer:
                log(f"\n>>> MISE A JOUR DISPONIBLE! <<<", f)
            else:
                log(f"\n>>> APPLICATION A JOUR <<<", f)
        log("", f)

        # 7. Recherche du Setup.exe
        log("[ETAPE 7] RECHERCHE DU FICHIER SETUP.EXE", f)
        log("-" * 40, f)

        if latest_release:
            assets = latest_release.get('assets', [])
            setup_found = False

            for asset in assets:
                name = asset.get('name', '').lower()
                if name.endswith('.exe') and ('setup' in name or 'install' in name):
                    log(f"Setup trouve: {asset.get('name')}", f)
                    log(f"URL: {asset.get('browser_download_url')}", f)
                    setup_found = True
                    break

            if not setup_found:
                log("ATTENTION: Aucun fichier Setup.exe trouve dans les assets!", f)
                log("Assets disponibles:", f)
                for asset in assets:
                    log(f"  - {asset.get('name')}", f)
        log("", f)

        # 8. Test de l'API Flask locale
        log("[ETAPE 8] TEST DE L'API FLASK LOCALE", f)
        log("-" * 40, f)

        try:
            api_url = "http://127.0.0.1:5001/api/updates/check"
            log(f"Test de: {api_url}", f)

            api_req = Request(api_url)
            with urlopen(api_req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
                log(f"Reponse API:", f)
                for key, value in data.items():
                    log(f"  {key}: {value}", f)
        except Exception as e:
            log(f"ERREUR (l'app doit etre en cours d'execution): {e}", f)
        log("", f)

        # Resume
        log("=" * 70, f)
        log("    RESUME", f)
        log("=" * 70, f)

        if releases and latest_release:
            latest_version = latest_release.get('tag_name', '0.0.0')
            is_newer = is_newer_version(latest_version, CURRENT_VERSION)

            log(f"Version actuelle: {CURRENT_VERSION}", f)
            log(f"Derniere version: {latest_version}", f)
            log(f"Mise a jour disponible: {'OUI' if is_newer else 'NON'}", f)
        else:
            log("ERREUR: Impossible de determiner le statut", f)

        log("", f)
        log(f"Rapport sauvegarde dans: {REPORT_FILE}", f)
        log("=" * 70, f)

    print(f"\n\nRapport sauvegarde dans: {REPORT_FILE}")
    print("Envoie le contenu de ce fichier pour diagnostic.")

if __name__ == '__main__':
    run_debug()
