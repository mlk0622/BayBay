#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bay Bay - Lanceur Principal
=====================================
Stocke les données dans %APPDATA% pour éviter les problèmes de permissions
"""

import os
import sys
import threading
import webbrowser
import time
import ctypes

# ========== Configuration ==========
APP_NAME = "Bay Bay"
VERSION = "2.3"
PORT = 5001
HOST = "127.0.0.1"

# Détection du mode Electron (variable d'environnement ou argument)
ELECTRON_MODE = os.environ.get('ELECTRON_MODE', '0') == '1' or '--electron' in sys.argv


def is_frozen():
    """Vérifie si on est en mode exe (PyInstaller)"""
    return getattr(sys, 'frozen', False)


def get_exe_dir():
    """Retourne le dossier où se trouve l'exe"""
    if is_frozen():
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_internal_dir():
    """Retourne le dossier _internal de PyInstaller ou le dossier source"""
    if is_frozen():
        return getattr(sys, '_MEIPASS', get_exe_dir())
    return os.path.dirname(os.path.abspath(__file__))


def get_user_data_dir():
    """
    Retourne le dossier de données utilisateur.
    Utilise %APPDATA%/BayBay pour éviter les problèmes de permissions.
    """
    if sys.platform == 'win32':
        # Windows: %APPDATA%\BayBay
        appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
        data_dir = os.path.join(appdata, 'BayBay')
    else:
        # Linux/Mac: ~/.baybay
        data_dir = os.path.join(os.path.expanduser('~'), '.baybay')

    return data_dir


def get_data_path():
    """Retourne le chemin des données utilisateur et le crée si nécessaire"""
    data_path = get_user_data_dir()
    try:
        os.makedirs(data_path, exist_ok=True)
    except PermissionError:
        # Fallback: utiliser un dossier temporaire
        import tempfile
        data_path = os.path.join(tempfile.gettempdir(), 'BayBay')
        os.makedirs(data_path, exist_ok=True)
    return data_path


def show_message_box(title, message, style=0):
    """Affiche une boîte de message Windows (seulement en mode non-Electron)"""
    if ELECTRON_MODE:
        return
    try:
        ctypes.windll.user32.MessageBoxW(0, message, title, style)
    except:
        print(f"{title}: {message}")


def is_first_run():
    """Vérifie si c'est le premier lancement"""
    marker_file = os.path.join(get_data_path(), ".installed")
    return not os.path.exists(marker_file)


def mark_as_installed():
    """Marque l'installation comme complète"""
    marker_file = os.path.join(get_data_path(), ".installed")
    with open(marker_file, 'w') as f:
        f.write(f"Installed: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Version: {VERSION}\n")


def setup_directories():
    """Crée les dossiers nécessaires dans le dossier de données utilisateur"""
    base = get_data_path()

    directories = [
        base,
        os.path.join(base, "uploads"),
        os.path.join(base, "uploads", "assurances"),
        os.path.join(base, "uploads", "etats_lieux"),
        os.path.join(base, "uploads", "etats_lieux", "photos"),
        os.path.join(base, "uploads", "etats_lieux", "drafts"),
        os.path.join(base, "uploads", "etats_lieux", "generated"),
        os.path.join(base, "uploads", "photos"),
        os.path.join(base, "uploads", "quittances"),
        os.path.join(base, "uploads", "appels_loyer"),
    ]

    for directory in directories:
        try:
            os.makedirs(directory, exist_ok=True)
        except Exception as e:
            if not ELECTRON_MODE:
                print(f"Warning: Cannot create {directory}: {e}")

    if not ELECTRON_MODE:
        print(f"📁 Dossiers créés dans: {base}")


def setup_environment():
    """Configure les variables d'environnement"""
    internal_dir = get_internal_dir()

    # Ajouter les chemins au sys.path
    if internal_dir not in sys.path:
        sys.path.insert(0, internal_dir)

    # Définir la variable d'environnement pour app.py
    os.environ['BAYBAY_DATA_DIR'] = get_data_path()
    # Partager la version runtime avec auto_updater.py
    os.environ['BAYBAY_VERSION'] = VERSION


def open_browser():
    """Ouvre le navigateur après un délai (seulement en mode standalone)"""
    if ELECTRON_MODE:
        return

    time.sleep(2)
    url = f"http://{HOST}:{PORT}"
    print(f"\n🌐 Ouverture du navigateur: {url}")
    webbrowser.open(url)


def print_banner():
    """Affiche la bannière de démarrage (seulement en mode standalone)"""
    if ELECTRON_MODE:
        return

    banner = f"""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║                    🏠 BAY BAY v{VERSION}                        ║
║                                                              ║
║       Application de gestion immobilière multi-niveaux      ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)


def run_first_time_setup():
    """Exécute la configuration initiale"""
    if not ELECTRON_MODE:
        print("\n🔧 Premier démarrage - Configuration initiale...\n")

    # Créer les dossiers
    setup_directories()

    # Marquer comme installé
    mark_as_installed()

    if not ELECTRON_MODE:
        print("\n✅ Configuration initiale terminée!\n")

    return True


def start_application():
    """Démarre l'application Flask"""
    try:
        # Importer l'application Flask
        from app import app, db

        # Enregistrer les routes de mise à jour (toujours, y compris en mode Electron)
        try:
            from auto_updater import register_update_routes
            register_update_routes(app)
            if not ELECTRON_MODE:
                print("🔄 Système de mise à jour activé")
        except ImportError as e:
            if not ELECTRON_MODE:
                print(f"⚠️  Système de mise à jour non disponible: {e}")

        # Créer les tables de la base de données
        with app.app_context():
            db.create_all()

        if not ELECTRON_MODE:
            print("✅ Base de données initialisée")
            print(f"📂 Données stockées dans: {get_data_path()}")
            print(f"\n🚀 Démarrage du serveur sur http://{HOST}:{PORT}")
            print("\n📋 Fonctionnalités disponibles:")
            print("   • Dashboard : Vue globale des loyers")
            print("   • Biens : Gestion des immeubles et appartements")
            print("   • Locataires : Gestion complète des locataires")
            print("   • Appels de loyer : Génération de documents PDF")
            print("   • Quittances : Édition de quittances PDF")
            print("   • Résumé : Synthèse mensuelle des loyers")
            print("   • Comptes : Suivi des paiements par locataire")
            print("\n" + "=" * 60)
            print("   Pour arrêter: fermez cette fenêtre ou Ctrl+C")
            print("=" * 60 + "\n")

            # Ouvrir le navigateur dans un thread séparé
            threading.Thread(target=open_browser, daemon=True).start()

        # Désactiver les logs Werkzeug en mode Electron
        if ELECTRON_MODE:
            import logging
            log = logging.getLogger('werkzeug')
            log.setLevel(logging.ERROR)

        # Lancer le serveur Flask
        app.run(
            host=HOST,
            port=PORT,
            debug=False,
            threaded=True,
            use_reloader=False
        )

    except ImportError as e:
        if not ELECTRON_MODE:
            print(f"\n❌ Erreur d'import: {e}")
            import traceback
            traceback.print_exc()
        show_message_box(
            "Erreur",
            f"Impossible de charger l'application:\n{e}",
            0x10
        )
        return False
    except Exception as e:
        if not ELECTRON_MODE:
            print(f"\n❌ Erreur: {e}")
            import traceback
            traceback.print_exc()
        show_message_box(
            "Erreur",
            f"Une erreur est survenue:\n{e}",
            0x10
        )
        return False

    return True


def main():
    """Point d'entrée principal"""
    print_banner()

    # Configurer l'environnement
    setup_environment()

    # Premier lancement?
    if is_first_run():
        if not run_first_time_setup():
            if not ELECTRON_MODE:
                input("\nAppuyez sur Entrée pour fermer...")
            sys.exit(1)
    else:
        # Vérifier quand même les dossiers
        setup_directories()

    # Démarrer l'application
    if not start_application():
        if not ELECTRON_MODE:
            input("\nAppuyez sur Entrée pour fermer...")
        sys.exit(1)


if __name__ == '__main__':
    main()
