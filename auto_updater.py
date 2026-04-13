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

# URL du serveur de mise à jour GitHub (endpoint /latest pour obtenir la derniere release)
UPDATE_SERVER_URL = "https://api.github.com/repos/mlk0622/BayBay/releases/latest"

# Version actuelle de l'application (fallback si BAYBAY_VERSION n'est pas defini)
CURRENT_VERSION = "3.0"
# Fichier de configuration local
CONFIG_FILE = "update_config.json"

# Nom de l'application pour la recherche du désinstallateur
APP_NAME = "Bay Bay"

# Fichier de log pour le debug
LOG_FILE = "updater_debug.log"

# Instance partagee pour conserver l'etat de progression entre les routes API.
_SHARED_UPDATER = None


def resolve_current_version(default_version=CURRENT_VERSION):
    """Retourne la version runtime de l'application si disponible."""
    # Priorite: version injectee par launcher.py au demarrage.
    env_version = os.environ.get('BAYBAY_VERSION', '').strip()
    if env_version:
        return env_version
    return default_version


def get_shared_updater():
    """Retourne une instance unique d'AutoUpdater pour conserver update_status."""
    global _SHARED_UPDATER
    if _SHARED_UPDATER is None:
        _SHARED_UPDATER = AutoUpdater()
    return _SHARED_UPDATER


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

    def __init__(self, current_version=None, server_url=UPDATE_SERVER_URL):
        self.current_version = current_version or resolve_current_version()
        self.server_url = server_url
        self.base_path = self._get_base_path()
        self.config = self._load_config()
        self.update_status = {
            'checking': False,
            'downloading': False,
            'installing': False,
            'progress': 0,
            'downloaded_mb': 0,
            'total_mb': 0,
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
        self.update_status['downloaded_mb'] = 0
        self.update_status['total_mb'] = 0
        self.update_status['message'] = 'Téléchargement en cours...'

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
                total_mb = (total_size / 1024 / 1024) if total_size > 0 else 0
                self.update_status['total_mb'] = round(total_mb, 1)

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
                            downloaded_mb = downloaded / 1024 / 1024
                            self.update_status['downloaded_mb'] = round(downloaded_mb, 1)
                            self.update_status['message'] = f"Téléchargement en cours... {percent:.1f}%"

                            # Logger tous les 10%
                            if int(percent / 10) > int(last_log_percent / 10):
                                log_debug(f"[AutoUpdater] Telechargement: {percent:.1f}% ({downloaded / 1024 / 1024:.1f} / {total_size / 1024 / 1024:.1f} MB)")
                                last_log_percent = percent

                            if progress_callback:
                                progress_callback(downloaded, total_size)
                        else:
                            downloaded_mb = downloaded / 1024 / 1024
                            self.update_status['downloaded_mb'] = round(downloaded_mb, 1)
                            self.update_status['message'] = f"Téléchargement en cours... {downloaded_mb:.1f} MB"

            log_debug(f"[AutoUpdater] Telechargement termine: {setup_path}")
            log_debug(f"[AutoUpdater] Taille fichier: {os.path.getsize(setup_path)} bytes")
            self.update_status['downloading'] = False
            self.update_status['progress'] = 100
            self.update_status['message'] = 'Téléchargement terminé'
            return setup_path

        except Exception as e:
            error_msg = f"Erreur de téléchargement : {e}"
            log_debug(f"[AutoUpdater] {error_msg}")
            log_debug(f"[AutoUpdater] Traceback: {traceback.format_exc()}")
            self.update_status['error'] = error_msg
            self.update_status['downloading'] = False
            return None

    def _get_install_status_path(self):
        """Retourne le chemin du fichier de statut d'installation (lu par le PS et Electron)."""
        user_data = self._get_user_data_dir()
        os.makedirs(user_data, exist_ok=True)
        return os.path.join(user_data, 'install_progress.txt')

    def _build_progress_powershell(self, status_file):
        """Genere le script PowerShell qui affiche la fenetre de progression d'installation."""
        # On utilise une chaine simple-quotee PowerShell pour le chemin (pas d'echappement de backslash).
        ps_status_literal = "'" + status_file.replace("'", "''") + "'"

        ps_template = r"""
$ErrorActionPreference = 'SilentlyContinue'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$statusFile = __STATUS_FILE__

$form = New-Object System.Windows.Forms.Form
$form.Text = 'Mise à jour Bay Bay'
$form.ClientSize = New-Object System.Drawing.Size(540, 230)
$form.StartPosition = 'CenterScreen'
$form.FormBorderStyle = 'FixedDialog'
$form.MaximizeBox = $false
$form.MinimizeBox = $true
$form.ControlBox = $true
$form.TopMost = $false
$form.ShowInTaskbar = $true
$form.BackColor = [System.Drawing.Color]::FromArgb(244, 247, 251)

$title = New-Object System.Windows.Forms.Label
$title.Text = 'Installation en cours...'
$title.Font = New-Object System.Drawing.Font('Segoe UI', 14, [System.Drawing.FontStyle]::Bold)
$title.ForeColor = [System.Drawing.Color]::FromArgb(31, 41, 55)
$title.Location = New-Object System.Drawing.Point(24, 22)
$title.Size = New-Object System.Drawing.Size(490, 28)
$title.BackColor = [System.Drawing.Color]::Transparent
$form.Controls.Add($title)

$sub = New-Object System.Windows.Forms.Label
$sub.Text = "Veuillez patienter, l'application va redémarrer automatiquement."
$sub.Font = New-Object System.Drawing.Font('Segoe UI', 9)
$sub.ForeColor = [System.Drawing.Color]::FromArgb(75, 85, 99)
$sub.Location = New-Object System.Drawing.Point(24, 54)
$sub.Size = New-Object System.Drawing.Size(490, 22)
$sub.BackColor = [System.Drawing.Color]::Transparent
$form.Controls.Add($sub)

$bgBar = New-Object System.Windows.Forms.Panel
$bgBar.Location = New-Object System.Drawing.Point(24, 100)
$bgBar.Size = New-Object System.Drawing.Size(490, 18)
$bgBar.BackColor = [System.Drawing.Color]::FromArgb(229, 231, 235)
$form.Controls.Add($bgBar)

$fillBar = New-Object System.Windows.Forms.Panel
$fillBar.Location = New-Object System.Drawing.Point(0, 0)
$fillBar.Size = New-Object System.Drawing.Size(0, 18)
$fillBar.BackColor = [System.Drawing.Color]::FromArgb(16, 185, 129)
$bgBar.Controls.Add($fillBar)

$percentLabel = New-Object System.Windows.Forms.Label
$percentLabel.Location = New-Object System.Drawing.Point(24, 128)
$percentLabel.Size = New-Object System.Drawing.Size(120, 22)
$percentLabel.Font = New-Object System.Drawing.Font('Segoe UI', 9)
$percentLabel.ForeColor = [System.Drawing.Color]::FromArgb(55, 65, 81)
$percentLabel.Text = '0%'
$percentLabel.BackColor = [System.Drawing.Color]::Transparent
$form.Controls.Add($percentLabel)

$hintLabel = New-Object System.Windows.Forms.Label
$hintLabel.Location = New-Object System.Drawing.Point(394, 128)
$hintLabel.Size = New-Object System.Drawing.Size(120, 22)
$hintLabel.Font = New-Object System.Drawing.Font('Segoe UI', 9)
$hintLabel.TextAlign = 'TopRight'
$hintLabel.ForeColor = [System.Drawing.Color]::FromArgb(55, 65, 81)
$hintLabel.Text = 'Installation'
$hintLabel.BackColor = [System.Drawing.Color]::Transparent
$form.Controls.Add($hintLabel)

$statusLabel = New-Object System.Windows.Forms.Label
$statusLabel.Location = New-Object System.Drawing.Point(24, 165)
$statusLabel.Size = New-Object System.Drawing.Size(490, 50)
$statusLabel.Font = New-Object System.Drawing.Font('Segoe UI', 9)
$statusLabel.ForeColor = [System.Drawing.Color]::FromArgb(55, 65, 81)
$statusLabel.Text = 'Démarrage de l''installation...'
$statusLabel.BackColor = [System.Drawing.Color]::Transparent
$form.Controls.Add($statusLabel)

# Table de traduction phase -> (percent, texte francais avec accents).
# Les accents sont stockes ici (fichier PS en UTF-8 BOM) plutot que dans le .bat
# car cmd.exe ne sait pas lire les accents UTF-8 meme avec chcp 65001.
$phases = @{
    'starting'    = @{ Percent =   5; Text = "Démarrage de l'installation..." }
    'closing'     = @{ Percent =  20; Text = "Fermeture de l'application..." }
    'installing'  = @{ Percent =  35; Text = "Installation des fichiers..." }
    'finalizing'  = @{ Percent =  95; Text = "Finalisation de la mise à jour..." }
    'done'        = @{ Percent = 100; Text = "Mise à jour terminée !" }
}

$script:targetPercent = 5
$script:currentPercent = 0
$script:done = $false
$script:closeAt = $null
$script:startTime = Get-Date
$script:maxDuration = 300  # timeout de securite: 5 minutes max

$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 60
$timer.Add_Tick({
    try {
        if (Test-Path $statusFile) {
            $lines = Get-Content -LiteralPath $statusFile -Encoding UTF8 -ErrorAction SilentlyContinue
            foreach ($line in $lines) {
                if ($line -match '^PHASE=(.+)') {
                    $key = $matches[1].Trim()
                    if ($phases.ContainsKey($key)) {
                        $p = $phases[$key]
                        if ([int]$p.Percent -gt $script:targetPercent) {
                            $script:targetPercent = [int]$p.Percent
                        }
                        $statusLabel.Text = $p.Text
                        if ($key -eq 'done') {
                            $script:done = $true
                            $script:targetPercent = 100
                        }
                    }
                } elseif ($line -match '^PERCENT=(\d+)') {
                    $val = [int]$matches[1]
                    if ($val -gt $script:targetPercent) { $script:targetPercent = $val }
                } elseif ($line -match '^STATUS=(.+)') {
                    $statusLabel.Text = $matches[1]
                } elseif ($line -match '^STATE=done') {
                    $script:done = $true
                    $script:targetPercent = 100
                }
            }
        }
    } catch {}

    # Timeout de securite: fermer apres 5 minutes quoi qu'il arrive
    $elapsed = ((Get-Date) - $script:startTime).TotalSeconds
    if ($elapsed -ge $script:maxDuration) {
        $script:done = $true
        $script:targetPercent = 100
    }

    if ($script:currentPercent -lt $script:targetPercent) {
        $script:currentPercent = [Math]::Min($script:currentPercent + 1, $script:targetPercent)
    } elseif (-not $script:done -and $script:currentPercent -lt 92) {
        # Avancement lent quand on attend l'installeur (pour donner du retour visuel)
        if ((Get-Random -Minimum 0 -Maximum 8) -eq 0) {
            $script:currentPercent = [Math]::Min($script:currentPercent + 1, 92)
        }
    }

    $width = [int]([Math]::Round(490 * ($script:currentPercent / 100)))
    if ($width -lt 0) { $width = 0 }
    if ($width -gt 490) { $width = 490 }
    $fillBar.Width = $width
    $percentLabel.Text = "$($script:currentPercent)%"

    if ($script:done -and $script:currentPercent -ge 100) {
        if ($null -eq $script:closeAt) {
            $script:closeAt = (Get-Date).AddMilliseconds(800)
        } elseif ((Get-Date) -ge $script:closeAt) {
            $timer.Stop()
            $form.Close()
        }
    }
})
$timer.Start()

[void]$form.ShowDialog()
"""
        return ps_template.replace("__STATUS_FILE__", ps_status_literal)

    def _build_kill_powershell(self, status_file):
        """Genere le script PowerShell qui tue activement les processus Bay Bay
        et attend que les handles fichier soient liberes par le noyau Windows."""
        ps_template = r"""
$ErrorActionPreference = 'SilentlyContinue'

# Noms de processus a tuer (sans .exe pour Get-Process / Stop-Process)
$names = @('BayBay', 'Bay Bay', 'electron')

function Kill-AllMatching {
    param($processNames)
    foreach ($n in $processNames) {
        Get-Process -Name $n -ErrorAction SilentlyContinue | ForEach-Object {
            try { $_.Kill() } catch {}
        }
    }
}

function Any-Alive {
    param($processNames)
    foreach ($n in $processNames) {
        if (Get-Process -Name $n -ErrorAction SilentlyContinue) {
            return $true
        }
    }
    return $false
}

# Premiere passe: kill agressif
Kill-AllMatching $names

# Boucle d'attente jusqu'a 30s, en re-tuant si necessaire
$deadline = (Get-Date).AddSeconds(30)
while ((Get-Date) -lt $deadline) {
    if (-not (Any-Alive $names)) { break }
    Kill-AllMatching $names
    Start-Sleep -Milliseconds 250
}

# Periode de grace pour que Windows libere les handles fichier
# (les handles ne sont pas synchroniquement liberes a la mort du process)
Start-Sleep -Seconds 3

exit 0
"""
        return ps_template

    def create_update_script(self, setup_path, silent_install=True):
        """
        Cree les scripts qui prennent en charge la mise a jour:
        - Un script PowerShell qui affiche une fenetre de progression d'installation
        - Un script batch qui orchestre: PS UI -> kill app -> installeur -> nettoyage

        Args:
            setup_path: Chemin du Setup.exe telecharge
            silent_install: Si True, installation silencieuse

        Returns:
            Chemin du script batch ou None
        """
        log_debug(f"[AutoUpdater] === DEBUT create_update_script ===")
        log_debug(f"[AutoUpdater] Setup path: {setup_path}")
        log_debug(f"[AutoUpdater] Silent install: {silent_install}")

        try:
            script_dir = os.path.dirname(setup_path)
            update_script = os.path.join(script_dir, '_baybay_update.bat')
            ps_script = os.path.join(script_dir, '_baybay_progress.ps1')
            kill_script = os.path.join(script_dir, '_baybay_kill.ps1')
            status_file = self._get_install_status_path()

            # Reinitialiser le fichier de statut (ASCII suffit, le PS UI traduit la phase)
            try:
                with open(status_file, 'w', encoding='utf-8') as f:
                    f.write("PHASE=starting\n")
            except Exception as e:
                log_debug(f"[AutoUpdater] Impossible d'initialiser status file: {e}")

            # Generer le script PowerShell d'UI (avec BOM pour que PS 5.1 lise bien les accents)
            ps_content = self._build_progress_powershell(status_file)
            with open(ps_script, 'w', encoding='utf-8-sig') as f:
                f.write(ps_content)
            log_debug(f"[AutoUpdater] Script PowerShell UI cree: {ps_script}")

            # Generer le script PowerShell qui tue les processus et attend la liberation des handles
            kill_content = self._build_kill_powershell(status_file)
            with open(kill_script, 'w', encoding='utf-8-sig') as f:
                f.write(kill_content)
            log_debug(f"[AutoUpdater] Script PowerShell kill cree: {kill_script}")

            # Commande d'installation: appel DIRECT de l'exe avec /S
            # (sans passer par PowerShell Start-Process qui peut manger les args).
            # Avec oneClick:true dans package.json + /S, l'install est 100% silencieux.
            if silent_install:
                install_cmd = f'"{setup_path}" /S'
            else:
                install_cmd = f'"{setup_path}"'

            # IMPORTANT: le .bat reste en ASCII pur (pas d'accents), car cmd.exe
            # ne lit pas correctement les bytes UTF-8 d'un fichier .bat meme avec
            # chcp 65001. Le bat ecrit uniquement des cles "PHASE=..." dans le
            # fichier de statut, et le script PowerShell d'UI traduit ces cles
            # vers du francais accentue (le .ps1 est en UTF-8 BOM, lu correctement).
            bat_lines = [
                '@echo off',
                'setlocal',
                f'set "STATUS_FILE={status_file}"',
                '',
                'REM === Lancement de la fenetre PowerShell de progression ===',
                f'start "" /B powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "{ps_script}"',
                '',
                'REM Laisser le temps a la fenetre de progression d\'apparaitre',
                'timeout /t 2 /nobreak >nul',
                '',
                'REM === Phase: closing (fermeture de l application) ===',
                '> "%STATUS_FILE%" echo PHASE=closing',
                '',
                'REM === Force-close de Bay Bay (backend + Electron, arbres complets) ===',
                'taskkill /F /T /IM BayBay.exe >nul 2>&1',
                'taskkill /F /T /IM "Bay Bay.exe" >nul 2>&1',
                'taskkill /F /T /IM electron.exe >nul 2>&1',
                '',
                'REM === Attendre activement que tous les processus soient morts',
                'REM     ET que le noyau ait libere les handles fichier (3s de grace) ===',
                f'powershell -NoProfile -ExecutionPolicy Bypass -File "{kill_script}"',
                '',
                'REM === Phase: installing (installation des fichiers) ===',
                '> "%STATUS_FILE%" echo PHASE=installing',
                '',
                'REM === Lancer l installeur (appel direct, synchrone) ===',
                install_cmd,
                '',
                'REM === Phase: finalizing ===',
                '> "%STATUS_FILE%" echo PHASE=finalizing',
                'timeout /t 1 /nobreak >nul',
                '',
                'REM === Phase: done ===',
                '> "%STATUS_FILE%" echo PHASE=done',
                '',
                'REM Laisser le temps a la fenetre de progression de se fermer proprement',
                'timeout /t 2 /nobreak >nul',
                '',
                'REM === Relancer l application apres la mise a jour ===',
                'set "APP_EXE=%LOCALAPPDATA%\\Programs\\Bay Bay\\Bay Bay.exe"',
                'if exist "%APP_EXE%" (',
                '    start "" "%APP_EXE%"',
                ')',
                '',
                'REM === Nettoyage du dossier temporaire ===',
                f'rmdir /s /q "{script_dir}" >nul 2>&1',
                '',
                'endlocal',
                'exit',
            ]
            # Le bat ne contient que de l'ASCII, on peut l'ecrire en UTF-8 sans risque
            with open(update_script, 'w', encoding='ascii', errors='replace') as f:
                f.write('\n'.join(bat_lines) + '\n')

            log_debug(f"[AutoUpdater] Script batch cree: {update_script}")
            return update_script

        except Exception as e:
            log_debug(f"[AutoUpdater] Erreur creation script: {e}")
            log_debug(f"[AutoUpdater] Traceback: {traceback.format_exc()}")
            self.update_status['error'] = str(e)
            return None

    def perform_update(self, silent_install=True, progress_callback=None, update_info=None):
        """
        Effectue le processus complet de mise à jour:
        1. Vérifie les mises à jour (sauf si update_info est fourni)
        2. Télécharge le Setup.exe
        3. Crée et lance le script de mise à jour
        4. Quitte l'application

        Args:
            silent_install: Si True, installation silencieuse
            progress_callback: Callback pour la progression
            update_info: Info de mise à jour pré-vérifiée (évite un appel API en double)

        Returns:
            True si mise à jour lancée, False sinon
        """
        log_debug(f"[AutoUpdater] === DEBUT perform_update ===")
        self.update_status['installing'] = True

        if not update_info:
            self.update_status['message'] = 'Vérification des mises à jour...'
            update_info = self.check_for_updates()

        if not update_info:
            log_debug("[AutoUpdater] Erreur: pas d'update_info")
            self.update_status['installing'] = False
            self.update_status['error'] = 'Impossible de vérifier les mises à jour'
            return False

        if not update_info.get('is_newer'):
            log_debug(f"[AutoUpdater] Pas de mise a jour (version actuelle: {self.current_version})")
            self.update_status['installing'] = False
            self.update_status['message'] = 'Application à jour'
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
        self.update_status['message'] = 'Téléchargement en cours...'
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
        self.update_status['message'] = 'Préparation de l\'installation...'
        update_script = self.create_update_script(setup_path, silent_install)

        if not update_script:
            log_debug("[AutoUpdater] Erreur: echec creation script")
            self.update_status['installing'] = False
            return False

        # Lancer le script et quitter
        log_debug("[AutoUpdater] Lancement du script de mise a jour...")
        log_debug(f"[AutoUpdater] Script: {update_script}")

        self.update_status['message'] = 'Lancement de l\'installation...'

        # Lancer le script en mode totalement masque (pas de fenetre CMD visible)
        # CREATE_NO_WINDOW empeche toute console d'apparaitre. La progression est
        # rendue par la fenetre PowerShell lancee par le script lui-meme.
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0  # SW_HIDE

            creationflags = subprocess.CREATE_NO_WINDOW
            # Tenter de detacher du job parent pour survivre au taskkill du backend
            try:
                creationflags |= subprocess.CREATE_BREAKAWAY_FROM_JOB
                subprocess.Popen(
                    ['cmd.exe', '/c', update_script],
                    creationflags=creationflags,
                    startupinfo=startupinfo,
                    close_fds=True
                )
            except OSError:
                # Le job parent n'autorise pas le breakaway, retomber sans ce flag
                subprocess.Popen(
                    ['cmd.exe', '/c', update_script],
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    startupinfo=startupinfo,
                    close_fds=True
                )
            log_debug("[AutoUpdater] Script lance avec succes (mode masque)")
        except Exception as e:
            log_debug(f"[AutoUpdater] Erreur lancement script: {e}")
            log_debug(f"[AutoUpdater] Traceback: {traceback.format_exc()}")
            self.update_status['error'] = str(e)
            return False

        log_debug("[AutoUpdater] Script lance, fermeture forcee du backend...")

        # Arret force du processus backend pour eviter qu'il bloque l'installation.
        try:
            if sys.platform == 'win32':
                subprocess.Popen(
                    ['taskkill', '/F', '/PID', str(os.getpid())],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
        except Exception as kill_err:
            log_debug(f"[AutoUpdater] Echec taskkill backend: {kill_err}")

        os._exit(0)


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
    log_debug(f"[Flask] CURRENT_VERSION (fallback) = {CURRENT_VERSION}")
    log_debug(f"[Flask] VERSION runtime detectee = {resolve_current_version()}")
    log_debug(f"[Flask] Fichier de log: {get_log_path()}")

    @app.route('/api/updates/check')
    def api_check_updates():
        """API pour vérifier les mises à jour"""
        log_debug(f"[API] === /api/updates/check appele ===")
        log_debug(f"[API] CURRENT_VERSION fallback = {CURRENT_VERSION}")
        log_debug(f"[API] CURRENT_VERSION runtime = {resolve_current_version()}")

        updater = get_shared_updater()
        log_debug(f"[API] updater.current_version = {updater.current_version}")

        result = updater.check_for_updates(silent=False)

        if result:
            log_debug(f"[API] Resultat: version={result.get('version')}, is_newer={result.get('is_newer')}")
            response = {
                'available': result.get('is_newer', False),
                'version': result.get('version'),
                'current_version': result.get('current_version', resolve_current_version()),
                'release_notes': result.get('release_notes'),
                'download_url': result.get('download_url'),
                'asset_name': result.get('asset_name')
            }
            log_debug(f"[API] Response: {response}")
            return jsonify(response)

        log_debug(f"[API] ERREUR: aucun resultat retourne")
        return jsonify({
            'available': False,
            'current_version': resolve_current_version(),
            'error': 'Impossible de verifier les mises a jour'
        })

    @app.route('/api/updates/download', methods=['POST'])
    def api_download_update():
        """API pour télécharger et installer une mise à jour"""
        log_debug(f"[API] === /api/updates/download appele ===")

        updater = get_shared_updater()
        updater.update_status['error'] = None
        updater.update_status['progress'] = 0
        updater.update_status['downloaded_mb'] = 0
        updater.update_status['total_mb'] = 0
        updater.update_status['message'] = 'Démarrage de la mise à jour...'

        # Récupérer les infos depuis la requête (envoyées par Electron)
        data = request.get_json() or {}
        silent_install = data.get('silent', True)

        # Construire update_info à partir des données de la requête
        # (évite un appel API GitHub en double — déjà vérifié par /check)
        download_url = data.get('download_url')
        asset_name = data.get('asset_name')
        version = data.get('version')

        if download_url:
            # Electron nous a transmis les infos, pas besoin de re-vérifier
            log_debug(f"[API] Update info recue d'Electron: version={version}")
            update_info = {
                'version': version,
                'download_url': download_url,
                'asset_name': asset_name,
                'is_newer': True,
                'current_version': resolve_current_version(),
            }
        else:
            # Fallback: re-vérifier auprès de GitHub
            log_debug("[API] Pas d'info Electron, re-verification GitHub...")
            update_info = updater.check_for_updates(silent=False)
            if not update_info or not update_info.get('is_newer'):
                log_debug("[API] Pas de mise a jour disponible")
                return jsonify({'success': False, 'message': 'Aucune mise a jour disponible'})
            download_url = update_info.get('download_url')

        if not download_url:
            log_debug("[API] Pas de download_url")
            return jsonify({'success': False, 'message': 'Aucun fichier Setup.exe disponible'})

        log_debug(f"[API] silent_install = {silent_install}")

        # Lancer la mise à jour dans un thread NON-daemon pour qu'il survive
        def do_update():
            log_debug("[API] Thread de mise a jour demarre")
            try:
                updater.perform_update(silent_install=silent_install, update_info=update_info)
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
        updater = get_shared_updater()

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
        updater = get_shared_updater()
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
