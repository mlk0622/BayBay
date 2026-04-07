from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, make_response, send_file, after_this_request
import json
import re
import html
from decimal import Decimal
from datetime import datetime, date
import os
import sys
import smtplib
from types import SimpleNamespace
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from werkzeug.utils import secure_filename


def get_user_data_dir():
    """
    Retourne le dossier de données utilisateur.
    Utilise la variable d'environnement si définie par launcher.py,
    sinon utilise %APPDATA%/BayBay.
    """
    # Vérifier si launcher.py a défini le chemin
    data_dir = os.environ.get('BAYBAY_DATA_DIR')
    if data_dir:
        return data_dir

    # Sinon, calculer le chemin
    if sys.platform == 'win32':
        appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
        data_dir = os.path.join(appdata, 'BayBay')
    else:
        data_dir = os.path.join(os.path.expanduser('~'), '.baybay')

    return data_dir


# Déterminer les chemins selon le mode d'exécution
if getattr(sys, 'frozen', False):
    # Mode PyInstaller (.exe)
    INTERNAL_DIR = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
else:
    # Mode développement
    INTERNAL_DIR = os.path.dirname(os.path.abspath(__file__))

# Dossier des données utilisateur (base de données, uploads, etc.)
USER_DATA_DIR = get_user_data_dir()
os.makedirs(USER_DATA_DIR, exist_ok=True)

# Configuration des chemins
TEMPLATE_FOLDER = os.path.join(INTERNAL_DIR, 'templates')
STATIC_FOLDER = os.path.join(INTERNAL_DIR, 'static')
UPLOAD_FOLDER = os.path.join(USER_DATA_DIR, 'uploads')
DATABASE_PATH = os.path.join(USER_DATA_DIR, 'gestion_locative.db')

# Importer models
from models import db, SCI, BienImmobilier, Appartement, Locataire, Paiement, AppelLoyer, Quittance, ProgrammationAppel, ConfigEmail, DocumentLocataire, EtatDesLieux, PhotoEtatLieux, PrefillPdfHistorique, StatutPaiement, StatutLocataire, TypeEtatLieux

app = Flask(__name__,
            template_folder=TEMPLATE_FOLDER,
            static_folder=STATIC_FOLDER)
app.config['SECRET_KEY'] = 'baybay-secret-key-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DATABASE_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Créer le dossier uploads s'il n'existe pas
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'assurances'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'etats_lieux'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'etats_lieux', 'photos'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'photos'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'quittances'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'appels_loyer'), exist_ok=True)

db.init_app(app)

with app.app_context():
    db.create_all()

def format_currency(value):
    if value is None:
        return "0,00 €"
    return f"{float(value):,.2f} €".replace(",", " ").replace(".", ",")

def format_date(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return value.strftime('%d/%m/%Y')

def format_datetime(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return value.strftime('%d/%m/%Y à %H:%M')

app.jinja_env.filters['currency'] = format_currency
app.jinja_env.filters['date_fr'] = format_date
app.jinja_env.filters['datetime_fr'] = format_datetime

MOIS_FR = {
    1: 'Janvier', 2: 'Février', 3: 'Mars', 4: 'Avril',
    5: 'Mai', 6: 'Juin', 7: 'Juillet', 8: 'Août',
    9: 'Septembre', 10: 'Octobre', 11: 'Novembre', 12: 'Décembre'
}

app.jinja_env.globals['MOIS_FR'] = MOIS_FR

# Fonction de génération HTML vers PDF
def html_to_pdf(html_content, output_path):
    """Convertit HTML en PDF et sauvegarde le fichier"""

    # 1) Priorité à xhtml2pdf (pure Python, fonctionne sans dépendances externes)
    try:
        from xhtml2pdf import pisa
        with open(output_path, "wb") as pdf_file:
            pisa_status = pisa.CreatePDF(html_content, dest=pdf_file)
            if not pisa_status.err:
                return True, None
            xhtml2pdf_error = f"xhtml2pdf error code: {pisa_status.err}"
    except Exception as e:
        xhtml2pdf_error = str(e)

    # 2) Fallback pdfkit/wkhtmltopdf
    try:
        import pdfkit
        options = {
            'page-size': 'A4',
            'margin-top': '0.6in',
            'margin-right': '0.6in',
            'margin-bottom': '0.6in',
            'margin-left': '0.6in',
            'encoding': 'UTF-8',
            'quiet': ''
        }
        pdfkit.from_string(html_content, output_path, options=options)
        return True, None
    except Exception as e:
        pdfkit_error = str(e)

    # 3) Fallback WeasyPrint
    try:
        from weasyprint import HTML, CSS
        HTML(string=html_content).write_pdf(output_path)
        return True, None
    except Exception as e:
        weasy_error = str(e)

    # 4) Fallback robuste: produit un PDF texte basique
    def _extract_text_lines(source_html):
        text = re.sub(r'(?is)<(script|style).*?>.*?</\1>', ' ', source_html)
        text = re.sub(r'(?i)<br\s*/?>', '\n', text)
        text = re.sub(r'(?i)</(p|div|h1|h2|h3|h4|h5|h6|li|tr|table|section)>', '\n', text)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = html.unescape(text)
        lines = [re.sub(r'\s+', ' ', line).strip() for line in text.splitlines()]
        return [line for line in lines if line]

    def _write_basic_pdf(lines, path):
        safe_lines = lines[:52] if lines else ["Document"]

        def _pdf_escape(s):
            return s.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')

        content_ops = ["BT", "/F1 11 Tf", "50 800 Td"]
        for line in safe_lines:
            clean = _pdf_escape(line[:120])
            content_ops.append(f"({clean}) Tj")
            content_ops.append("0 -14 Td")
        content_ops.append("ET")

        content_stream = "\n".join(content_ops).encode('latin-1', errors='replace')

        objects = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
            b"<< /Length " + str(len(content_stream)).encode('ascii') + b" >>\nstream\n" + content_stream + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
        ]

        pdf_data = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]

        for index, obj in enumerate(objects, start=1):
            offsets.append(len(pdf_data))
            pdf_data.extend(f"{index} 0 obj\n".encode('ascii'))
            pdf_data.extend(obj)
            pdf_data.extend(b"\nendobj\n")

        xref_pos = len(pdf_data)
        pdf_data.extend(f"xref\n0 {len(objects) + 1}\n".encode('ascii'))
        pdf_data.extend(b"0000000000 65535 f \n")
        for off in offsets[1:]:
            pdf_data.extend(f"{off:010d} 00000 n \n".encode('ascii'))

        pdf_data.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode('ascii'))
        pdf_data.extend(f"startxref\n{xref_pos}\n%%EOF\n".encode('ascii'))

        with open(path, 'wb') as pdf_file:
            pdf_file.write(pdf_data)

    try:
        fallback_lines = _extract_text_lines(html_content)
        _write_basic_pdf(fallback_lines, output_path)
        return True, None
    except Exception as fallback_error:
        return False, f"xhtml2pdf: {xhtml2pdf_error}; pdfkit: {pdfkit_error}; WeasyPrint: {weasy_error}; Fallback: {fallback_error}"


def remplir_etat_des_lieux_modele(pdf_modele_path, pdf_sortie_path, donnees):
    """Remplit un PDF modele via coordonnees avec PyMuPDF (fitz)."""
    try:
        import fitz
    except Exception as e:
        return False, f"PyMuPDF indisponible: {e}"

    def _find_anchor_rect(page, labels, occurrence=0):
        for label in labels:
            matches = page.search_for(label)
            if len(matches) > occurrence:
                return matches[occurrence]
        return None

    def _insert_near_anchor(page, labels, texte, x_offset=2, y_offset=-1, fontsize=10.5, occurrence=0):
        value = str(texte or "").strip()
        if not value:
            return False
        rect = _find_anchor_rect(page, labels, occurrence)
        if not rect:
            return False
        page.insert_text(
            (rect.x1 + x_offset, rect.y1 + y_offset),
            value,
            fontsize=fontsize,
            fontname="helv",
            color=(0, 0, 0)
        )
        return True

    def _insert_checkbox(page, labels, x_offset=-12, y_offset=-1, fontsize=12):
        """Insert a checkmark before the label (checkbox style)."""
        rect = _find_anchor_rect(page, labels, 0)
        if not rect:
            return False
        page.insert_text(
            (rect.x0 + x_offset, rect.y1 + y_offset),
            "X",
            fontsize=fontsize,
            fontname="helv",
            color=(0, 0, 0)
        )
        return True

    try:
        doc = fitz.open(pdf_modele_path)

        # Compatibilite: remplissage brut par coordonnees si present.
        for page_key, champs in donnees.get("page_coords", {}).items():
            if not page_key.startswith("page_"):
                continue

            try:
                page_index = int(page_key.split("_")[1]) - 1
            except Exception:
                continue

            if page_index < 0 or page_index >= len(doc):
                continue

            page = doc[page_index]
            for champ in champs:
                texte = str(champ.get("texte", "") or "").strip()
                if not texte:
                    continue
                page.insert_text(
                    (float(champ.get("x", 0)), float(champ.get("y", 0))),
                    texte,
                    fontsize=float(champ.get("fontsize", 11)),
                    fontname=champ.get("fontname", "helv"),
                    color=champ.get("color", (0, 0, 0))
                )

        # Mode recommande: ancrage sur libelles du modele.
        page = doc[0]
        anchors = donnees.get("anchors", {})

        _insert_near_anchor(page, ["Adresse du logement :"], anchors.get("adresse_logement"), x_offset=1, y_offset=-2)
        _insert_near_anchor(page, ["Nom (ou denomination) :", "Nom (ou dénomination) :"], anchors.get("bailleur_nom"), x_offset=1, y_offset=-2)
        _insert_near_anchor(page, ["Domicile (ou siege social) :", "Domicile (ou siège social) :"], anchors.get("bailleur_adresse"), x_offset=1, y_offset=-2)
        _insert_near_anchor(page, ["Date d’entree :", "Date d’entrée :"], anchors.get("date_entree"), x_offset=1, y_offset=-2)
        _insert_near_anchor(page, ["Sortie :"], anchors.get("date_sortie"), x_offset=1, y_offset=-2)
        _insert_near_anchor(page, ["Le locataire :"], anchors.get("locataire_nom"), x_offset=1, y_offset=-2)
        _insert_near_anchor(page, ["Observations ou reserves :", "Observations ou réserves :"], anchors.get("observations"), x_offset=0, y_offset=12)

        # Cocher la case appropriee (entree ou sortie)
        if anchors.get("is_entree"):
            _insert_checkbox(page, ["ENTREE", "ENTRÉE", "Entree", "Entrée"])
        else:
            _insert_checkbox(page, ["SORTIE", "Sortie"])

        doc.save(pdf_sortie_path)
        doc.close()
        return True, None
    except Exception as e:
        return False, str(e)

# Fonction d'envoi d'email
def envoyer_email(expediteur, mot_de_passe, destinataire, sujet, corps, piece_jointe=None, serveur='smtp.gmail.com', port=587, use_tls=True):
    try:
        print(f"[DEBUG] Tentative de connexion a {serveur}:{port}")
        print(f"[DEBUG] Expediteur: {expediteur}")
        print(f"[DEBUG] Destinataire: {destinataire}")

        msg = MIMEMultipart()
        msg['From'] = expediteur
        msg['To'] = destinataire
        msg['Subject'] = sujet

        msg.attach(MIMEText(corps, 'html'))

        if piece_jointe:
            with open(piece_jointe, 'rb') as f:
                part = MIMEApplication(f.read(), Name=os.path.basename(piece_jointe))
                part['Content-Disposition'] = f'attachment; filename="{os.path.basename(piece_jointe)}"'
                msg.attach(part)

        print("[DEBUG] Creation du serveur SMTP...")
        if use_tls:
            server = smtplib.SMTP(serveur, port)
            print("[DEBUG] Activation TLS...")
            server.starttls()
        elif int(port) == 465:
            server = smtplib.SMTP_SSL(serveur, port)
        else:
            server = smtplib.SMTP(serveur, port)
        print("[DEBUG] Tentative de connexion...")
        server.login(expediteur, mot_de_passe)
        print("[DEBUG] Envoi du message...")
        server.send_message(msg)
        server.quit()
        print("[OK] Email envoye avec succes")
        return True, "Email envoyé avec succès"
    except smtplib.SMTPAuthenticationError as e:
        error_msg = f"ERREUR D'AUTHENTIFICATION: {str(e)}"
        if 'gmail.com' in expediteur.lower():
            error_msg += "\n\nSOLUTION POUR GMAIL:\n"
            error_msg += "1. Activez la validation en 2 étapes sur votre compte Google\n"
            error_msg += "2. Générez un 'Mot de passe d'application' spécifique\n"
            error_msg += "3. Utilisez ce mot de passe d'application au lieu de votre mot de passe habituel\n"
            error_msg += "4. Guide: https://support.google.com/accounts/answer/185833"
        print(f"[ERROR] {error_msg}")
        return False, error_msg
    except smtplib.SMTPConnectError as e:
        error_msg = f"ERREUR DE CONNEXION au serveur {serveur}:{port} - {str(e)}"
        print(f"[ERROR] {error_msg}")
        return False, error_msg
    except smtplib.SMTPServerDisconnected as e:
        error_msg = f"CONNEXION FERMÉE par le serveur - {str(e)}"
        print(f"[ERROR] {error_msg}")
        return False, error_msg
    except Exception as e:
        error_msg = f"ERREUR GÉNÉRALE: {str(e)}"
        print(f"[ERROR] {error_msg}")
        return False, error_msg


def _build_email_quittance(locataire, quittance, sci=None, modele_email='standard'):
    periode = f"{MOIS_FR[quittance.mois]} {quittance.annee}"
    nom_sci = sci.nom if sci else "Votre bailleur"
    prenom = locataire.prenom or locataire.nom

    if modele_email == 'court':
        sujet = f"Quittance - {periode}"
        corps = f"""
        <html><body style=\"font-family:Arial,sans-serif;line-height:1.6;color:#111827;\">
            <p>Bonjour {prenom},</p>
            <p>Veuillez trouver votre quittance de loyer ({periode}) en pièce jointe.</p>
            <p>Cordialement,<br><strong>{nom_sci}</strong></p>
        </body></html>
        """
        return sujet, corps

    sujet = f"Quittance de loyer - {periode}"
    corps = f"""
    <html><body style=\"font-family:Arial,sans-serif;line-height:1.6;color:#111827;\">
        <p>Bonjour {prenom} {locataire.nom},</p>
        <p>Veuillez trouver ci-joint votre quittance de loyer pour <strong>{periode}</strong>.</p>
        <p><strong>Montant payé :</strong> {format_currency(quittance.montant_paye)}</p>
        <p>Cordialement,<br><strong>{nom_sci}</strong></p>
    </body></html>
    """
    return sujet, corps


def _build_email_appel(locataire, appel, sci=None, modele_email='standard'):
    periode = f"{MOIS_FR[appel.mois]} {appel.annee}"
    nom_sci = sci.nom if sci else "Votre bailleur"
    prenom = locataire.prenom or locataire.nom
    total = format_currency(appel.total_avec_arrieres if (appel.arrieres and appel.arrieres > 0) else appel.total)
    echeance = format_date(appel.date_echeance) if appel.date_echeance else "Non définie"

    if modele_email == 'rappel':
        sujet = f"Rappel - Appel de loyer {periode}"
        corps = f"""
        <html><body style=\"font-family:Arial,sans-serif;line-height:1.6;color:#111827;\">
            <p>Bonjour {prenom},</p>
            <p>Rappel de votre appel de loyer pour <strong>{periode}</strong>.</p>
            <p><strong>Total à régler :</strong> {total}</p>
            <p><strong>Date d'échéance :</strong> {echeance}</p>
            <p>Le détail est joint en PDF.</p>
            <p>Cordialement,<br><strong>{nom_sci}</strong></p>
        </body></html>
        """
        return sujet, corps

    sujet = f"Appel de loyer - {periode}"
    corps = f"""
    <html><body style=\"font-family:Arial,sans-serif;line-height:1.6;color:#111827;\">
        <p>Bonjour {prenom} {locataire.nom},</p>
        <p>Veuillez trouver ci-joint votre appel de loyer pour <strong>{periode}</strong>.</p>
        <p><strong>Total à payer :</strong> {total}</p>
        <p><strong>Date d'échéance :</strong> {echeance}</p>
        <p>Cordialement,<br><strong>{nom_sci}</strong></p>
    </body></html>
    """
    return sujet, corps


def _generate_quittance_pdf_file(quittance, force_regenerate=False):
    locataire = quittance.locataire
    appartement = locataire.appartement
    bien = appartement.bien if appartement else None
    sci = bien.sci if bien else None

    html_content = render_template(
        'pdf/quittance.html',
        quittance=quittance,
        locataire=locataire,
        appartement=appartement,
        bien=bien,
        sci=sci,
        mois_fr=MOIS_FR
    )

    periode = f"{quittance.annee}_{quittance.mois:02d}"
    raw_name = f"quittance_{quittance.id}_{locataire.nom}_{locataire.prenom}_{periode}.pdf"
    pdf_filename = secure_filename(raw_name)
    pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], 'quittances', pdf_filename)
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

    if os.path.exists(pdf_path) and not force_regenerate:
        return pdf_path, None

    ok, error = html_to_pdf(html_content, pdf_path)
    if not ok:
        return None, error

    return pdf_path, None


def _generate_appel_pdf_file(appel, force_regenerate=False):
    locataire = appel.locataire
    appartement = locataire.appartement
    bien = appartement.bien if appartement else None
    sci = bien.sci if bien else None

    html_content = render_template(
        'pdf/appel_loyer.html',
        appel=appel,
        locataire=locataire,
        appartement=appartement,
        bien=bien,
        sci=sci,
        mois_fr=MOIS_FR
    )

    periode = f"{appel.annee}_{appel.mois:02d}"
    raw_name = f"appel_loyer_{appel.id}_{locataire.nom}_{locataire.prenom}_{periode}.pdf"
    pdf_filename = secure_filename(raw_name)
    pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], 'appels_loyer', pdf_filename)
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

    if os.path.exists(pdf_path) and not force_regenerate:
        return pdf_path, None

    ok, error = html_to_pdf(html_content, pdf_path)
    if not ok:
        return None, error

    return pdf_path, None

@app.route('/')
def dashboard():
    scis = SCI.query.all()
    locataires_actifs = Locataire.query.filter_by(statut=StatutLocataire.ACTIF).all()

    mois_actuel = date.today().month
    annee_actuelle = date.today().year

    total_attendu = Decimal('0.00')
    total_encaisse = Decimal('0.00')

    for loc in locataires_actifs:
        if loc.appartement:
            total_attendu += loc.total_mensuel
            paiement = loc.get_paiement_mois(mois_actuel, annee_actuelle)
            if paiement:
                total_encaisse += Decimal(str(paiement.montant_paye))

    reste_global = total_attendu - total_encaisse

    impayes = []
    for loc in locataires_actifs:
        if loc.appartement:
            paiement = loc.get_paiement_mois(mois_actuel, annee_actuelle)
            montant_paye = Decimal(str(paiement.montant_paye)) if paiement else Decimal('0.00')
            reste = loc.total_mensuel - montant_paye
            if reste > 0:
                statut = "Partiel" if montant_paye > 0 else "Impayé"
                impayes.append({
                    'sci': loc.appartement.bien.sci.nom,
                    'bien': loc.appartement.bien.adresse,
                    'appartement': loc.appartement.numero_porte,
                    'locataire': loc.nom_complet,
                    'locataire_id': loc.id,
                    'reste': float(reste),
                    'statut': statut
                })

    impayes.sort(key=lambda x: x['reste'], reverse=True)

    return render_template('dashboard.html',
                         scis=scis,
                         total_attendu=total_attendu,
                         total_encaisse=total_encaisse,
                         reste_global=reste_global,
                         impayes=impayes[:10],
                         mois_actuel=MOIS_FR[mois_actuel],
                         annee_actuelle=annee_actuelle)

@app.route('/sci/<int:sci_id>')
def vue_sci(sci_id):
    sci = SCI.query.get_or_404(sci_id)
    return render_template('sci_detail.html', sci=sci)

@app.route('/biens')
def liste_biens():
    biens = BienImmobilier.query.all()
    scis = SCI.query.all()
    return render_template('biens.html', biens=biens, scis=scis)

@app.route('/bien/<int:bien_id>')
def vue_bien(bien_id):
    bien = BienImmobilier.query.get_or_404(bien_id)
    return render_template('bien_detail.html', bien=bien)

@app.route('/locataires')
def liste_locataires():
    locataires = Locataire.query.order_by(Locataire.nom).all()
    appartements = Appartement.query.all()
    return render_template('locataires.html', locataires=locataires, appartements=appartements)

@app.route('/locataire/<int:locataire_id>/resume')
def vue_locataire(locataire_id):
    # Route legacy: redirige vers la fiche complète pour conserver les anciens liens.
    return redirect(url_for('locataire_detail', id=locataire_id))

@app.route('/appels-loyer')
def appels_loyer():
    locataires = Locataire.query.filter_by(statut=StatutLocataire.ACTIF).all()
    appels = AppelLoyer.query.order_by(AppelLoyer.annee.desc(), AppelLoyer.mois.desc()).all()
    config_email = ConfigEmail.query.first()
    mois_actuel = date.today().month
    annee_actuelle = date.today().year
    return render_template('appels_loyer.html',
                         locataires=locataires,
                         appels=appels,
                         config_email=config_email,
                         mois_actuel=mois_actuel,
                         annee_actuelle=annee_actuelle)

@app.route('/quittances')
def quittances():
    locataires = Locataire.query.filter_by(statut=StatutLocataire.ACTIF).all()
    quittances_list = Quittance.query.order_by(Quittance.annee.desc(), Quittance.mois.desc()).all()
    mois_actuel = date.today().month
    annee_actuelle = date.today().year
    return render_template('quittances.html',
                         locataires=locataires,
                         quittances=quittances_list,
                         mois_actuel=mois_actuel,
                         annee_actuelle=annee_actuelle)

@app.route('/resume-loyers')
def resume_loyers():
    # Récupérer les paramètres ou utiliser les valeurs par défaut
    nb_mois = request.args.get('nb_mois', 6, type=int)  # Nombre de mois à afficher

    locataires_actifs = Locataire.query.filter_by(statut=StatutLocataire.ACTIF).all()

    # Générer la liste des mois à afficher (du plus récent au plus ancien)
    mois_liste = []
    mois_courant = date.today().month
    annee_courante = date.today().year

    for i in range(nb_mois):
        mois_liste.append({'mois': mois_courant, 'annee': annee_courante})
        mois_courant -= 1
        if mois_courant < 1:
            mois_courant = 12
            annee_courante -= 1

    # Calculer les données par mois
    donnees_par_mois = []
    total_global_attendu = Decimal('0.00')
    total_global_encaisse = Decimal('0.00')

    for periode in mois_liste:
        m, a = periode['mois'], periode['annee']
        locataires_mois = []
        total_attendu_mois = Decimal('0.00')
        total_encaisse_mois = Decimal('0.00')
        nb_paye = 0
        nb_partiel = 0
        nb_impaye = 0

        for loc in locataires_actifs:
            if loc.appartement and loc.date_debut_bail:
                # Vérifier si le bail était actif pendant ce mois
                date_mois = date(a, m, 1)

                # Le bail doit avoir commencé avant ou pendant le mois
                if loc.date_debut_bail > date_mois:
                    # Le bail n'avait pas encore commencé ce mois-là
                    continue

                # Si date_fin_bail existe, vérifier qu'elle n'est pas avant le mois
                if loc.date_fin_bail and loc.date_fin_bail < date_mois:
                    # Le bail était déjà terminé ce mois-là
                    continue

                paiement = loc.get_paiement_mois(m, a)
                montant_paye = Decimal(str(paiement.montant_paye)) if paiement else Decimal('0.00')
                date_paiement = paiement.date_paiement if paiement else None
                reste = loc.total_mensuel - montant_paye

                if montant_paye >= loc.total_mensuel:
                    statut = 'Payé'
                    nb_paye += 1
                elif montant_paye > 0:
                    statut = 'Partiel'
                    nb_partiel += 1
                else:
                    statut = 'Impayé'
                    nb_impaye += 1

                locataires_mois.append({
                    'locataire': loc,
                    'loyer': loc.loyer_actuel,
                    'charges': loc.charges_actuelles,
                    'total': loc.total_mensuel,
                    'paye': montant_paye,
                    'reste': reste,
                    'date_paiement': date_paiement,
                    'statut': statut
                })

                total_attendu_mois += loc.total_mensuel
                total_encaisse_mois += montant_paye

        donnees_par_mois.append({
            'mois': m,
            'annee': a,
            'locataires': locataires_mois,
            'total_attendu': total_attendu_mois,
            'total_encaisse': total_encaisse_mois,
            'reste': total_attendu_mois - total_encaisse_mois,
            'nb_paye': nb_paye,
            'nb_partiel': nb_partiel,
            'nb_impaye': nb_impaye
        })

        total_global_attendu += total_attendu_mois
        total_global_encaisse += total_encaisse_mois

    return render_template('resume_loyers.html',
                         donnees_par_mois=donnees_par_mois,
                         total_global_attendu=total_global_attendu,
                         total_global_encaisse=total_global_encaisse,
                         reste_global=total_global_attendu - total_global_encaisse,
                         nb_mois=nb_mois)

@app.route('/compte-locatif/<int:locataire_id>')
def compte_locatif(locataire_id):
    locataire = Locataire.query.get_or_404(locataire_id)

    # Utiliser l'historique complet qui inclut tous les mois depuis le début du bail
    historique = locataire.get_historique_complet()

    # Calculer les totaux
    total_du = sum(h['total'] for h in historique)
    total_paye = sum(h['paye'] for h in historique)
    solde_global = sum(h['reste'] for h in historique)

    return render_template('compte_locatif.html',
                          locataire=locataire,
                          historique=historique,
                          total_du=total_du,
                          total_paye=total_paye,
                          solde_global=solde_global)

@app.route('/comptes-locatifs')
def comptes_locatifs():
    locataires = Locataire.query.filter_by(statut=StatutLocataire.ACTIF).order_by(Locataire.nom).all()
    mois_actuel = date.today().month
    annee_actuelle = date.today().year

    donnees = []
    for loc in locataires:
        if loc.appartement:
            paiement = loc.get_paiement_mois(mois_actuel, annee_actuelle)
            montant_paye = Decimal(str(paiement.montant_paye)) if paiement else Decimal('0.00')
            date_paiement = paiement.date_paiement if paiement else None

            donnees.append({
                'locataire': loc,
                'loyer': loc.loyer_actuel,
                'charges': loc.charges_actuelles,
                'total': loc.total_mensuel,
                'paye': montant_paye,
                'impaye': loc.total_mensuel - montant_paye,
                'date_paiement': date_paiement
            })

    return render_template('comptes_locatifs.html', donnees=donnees, mois=mois_actuel, annee=annee_actuelle)

@app.route('/locataire/<int:id>')
def locataire_detail(id):
    locataire = Locataire.query.get_or_404(id)
    etats_lieux = EtatDesLieux.query.filter_by(locataire_id=id).order_by(EtatDesLieux.date_etat.desc()).all()
    assurance = DocumentLocataire.query.filter_by(locataire_id=id, type_document='assurance').first()
    bail = DocumentLocataire.query.filter_by(locataire_id=id, type_document='bail').first()
    photo = DocumentLocataire.query.filter_by(locataire_id=id, type_document='photo')\
        .order_by(DocumentLocataire.created_at.desc()).first()
    photo_token = int(photo.created_at.timestamp()) if photo and photo.created_at else int(datetime.now().timestamp())

    return render_template('locataire_detail.html',
                         locataire=locataire,
                         etats_lieux=etats_lieux,
                         assurance=assurance,
                         bail=bail,
                         photo=photo,
                         photo_token=photo_token,
                         now=datetime.now())

# Programmation des appels de loyer
@app.route('/programmation')
def programmation():
    programmations = ProgrammationAppel.query.order_by(ProgrammationAppel.date_envoi.desc()).all()
    locataires = Locataire.query.filter_by(statut=StatutLocataire.ACTIF).all()
    config_email = ConfigEmail.query.first()

    return render_template('programmation.html',
                         programmations=programmations,
                         locataires=locataires,
                         config_email=config_email)

# Page de gestion des documents
@app.route('/documents')
def documents():
    # Récupérer tous les locataires avec leurs documents
    locataires = Locataire.query.all()

    # Statistiques générales
    total_etats_lieux = EtatDesLieux.query.count()
    etats_avec_pdf = EtatDesLieux.query.filter(EtatDesLieux.chemin_fichier.isnot(None)).count()
    total_assurances = DocumentLocataire.query.filter_by(type_document='assurance').count()
    total_photos = DocumentLocataire.query.filter_by(type_document='photo').count()

    # États des lieux récents
    etats_recents = EtatDesLieux.query.order_by(EtatDesLieux.created_at.desc()).limit(10).all()

    # Documents d'assurance récents
    assurances_recentes = DocumentLocataire.query.filter_by(type_document='assurance')\
                         .order_by(DocumentLocataire.created_at.desc()).limit(10).all()

    # Photos récentes
    photos_recentes = DocumentLocataire.query.filter_by(type_document='photo')\
                     .order_by(DocumentLocataire.created_at.desc()).limit(10).all()

    return render_template('documents.html',
                         locataires=locataires,
                         total_etats_lieux=total_etats_lieux,
                         etats_avec_pdf=etats_avec_pdf,
                         total_assurances=total_assurances,
                         total_photos=total_photos,
                         etats_recents=etats_recents,
                         assurances_recentes=assurances_recentes,
                         photos_recentes=photos_recentes)

# Page États des lieux (nouvel onglet)
@app.route('/etats-lieux')
def etats_lieux():
    # Récupérer tous les états des lieux
    all_etats = EtatDesLieux.query.order_by(EtatDesLieux.date_etat.desc()).all()
    locataires = Locataire.query.filter_by(statut=StatutLocataire.ACTIF).order_by(Locataire.nom).all()

    # Statistiques
    stats = {
        'total': len(all_etats),
        'entrees': sum(1 for e in all_etats if e.type_etat == TypeEtatLieux.ENTREE),
        'sorties': sum(1 for e in all_etats if e.type_etat == TypeEtatLieux.SORTIE),
        'avec_pdf': sum(1 for e in all_etats if e.chemin_fichier)
    }

    prefill_history = PrefillPdfHistorique.query.order_by(PrefillPdfHistorique.created_at.desc()).limit(10).all()

    return render_template('etats_lieux.html',
                         etats_lieux=all_etats,
                         locataires=locataires,
                         stats=stats,
                         prefill_history=prefill_history)

# Configuration email
@app.route('/parametres')
def parametres():
    config_email = ConfigEmail.query.first()
    return render_template('parametres.html', config_email=config_email)

# API Routes
@app.route('/api/sci', methods=['POST'])
def create_sci():
    data = request.json
    sci = SCI(
        nom=data['nom'],
        ville=data['ville'],
        siret=data.get('siret'),
        adresse=data.get('adresse'),
        code_postal=data.get('code_postal'),
        email=data.get('email')
    )
    db.session.add(sci)
    db.session.commit()
    return jsonify({'success': True, 'id': sci.id})

@app.route('/api/sci/<int:sci_id>', methods=['GET'])
def get_sci(sci_id):
    """Récupérer les données d'une SCI"""
    sci = SCI.query.get_or_404(sci_id)
    return jsonify({
        'id': sci.id,
        'nom': sci.nom,
        'ville': sci.ville,
        'siret': sci.siret,
        'adresse': sci.adresse,
        'code_postal': sci.code_postal,
        'email': sci.email
    })

@app.route('/api/sci/<int:sci_id>', methods=['PUT'])
def update_sci(sci_id):
    sci = SCI.query.get_or_404(sci_id)
    data = request.json
    if 'nom' in data:
        sci.nom = data['nom']
    if 'ville' in data:
        sci.ville = data['ville']
    if 'siret' in data:
        sci.siret = data['siret']
    if 'adresse' in data:
        sci.adresse = data['adresse']
    if 'code_postal' in data:
        sci.code_postal = data['code_postal']
    if 'email' in data:
        sci.email = data['email']
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/sci/<int:sci_id>', methods=['DELETE'])
def delete_sci(sci_id):
    sci = SCI.query.get_or_404(sci_id)
    db.session.delete(sci)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/bien', methods=['POST'])
def create_bien():
    data = request.json
    bien = BienImmobilier(
        adresse=data['adresse'],
        code_postal=data.get('code_postal'),
        ville=data.get('ville'),
        type_bien=data['type_bien'],
        sci_id=data['sci_id']
    )
    db.session.add(bien)
    db.session.commit()
    return jsonify({'success': True, 'id': bien.id})

@app.route('/api/bien/<int:bien_id>', methods=['PUT'])
def update_bien(bien_id):
    bien = BienImmobilier.query.get_or_404(bien_id)
    data = request.json
    if 'adresse' in data:
        bien.adresse = data['adresse']
    if 'code_postal' in data:
        bien.code_postal = data['code_postal']
    if 'ville' in data:
        bien.ville = data['ville']
    if 'type_bien' in data:
        bien.type_bien = data['type_bien']
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/bien/<int:bien_id>', methods=['DELETE'])
def delete_bien(bien_id):
    bien = BienImmobilier.query.get_or_404(bien_id)
    db.session.delete(bien)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/appartement', methods=['POST'])
def create_appartement():
    data = request.json
    appart = Appartement(
        numero_porte=data['numero_porte'],
        type_appartement=data['type_appartement'],
        surface=Decimal(str(data.get('surface', 0))) if data.get('surface') else None,
        loyer_mensuel=Decimal(str(data.get('loyer_mensuel', 0))) if data.get('loyer_mensuel') else None,
        charges=Decimal(str(data.get('charges', 0))) if data.get('charges') else None,
        nb_pieces=int(data.get('nb_pieces')) if data.get('nb_pieces') else None,
        etage=data.get('etage'),
        bien_id=data['bien_id']
    )
    db.session.add(appart)
    db.session.commit()
    return jsonify({'success': True, 'id': appart.id})

@app.route('/api/appartement/<int:appart_id>', methods=['PUT'])
def update_appartement(appart_id):
    appart = Appartement.query.get_or_404(appart_id)
    data = request.json
    if 'numero_porte' in data:
        appart.numero_porte = data['numero_porte']
    if 'type_appartement' in data:
        appart.type_appartement = data['type_appartement']
    if 'surface' in data:
        appart.surface = Decimal(str(data['surface'])) if data['surface'] else None
    if 'loyer_mensuel' in data:
        appart.loyer_mensuel = Decimal(str(data['loyer_mensuel'])) if data['loyer_mensuel'] else None
    if 'charges' in data:
        appart.charges = Decimal(str(data['charges'])) if data['charges'] else None
    if 'nb_pieces' in data:
        appart.nb_pieces = int(data['nb_pieces']) if data['nb_pieces'] else None
    if 'etage' in data:
        appart.etage = data['etage']
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/appartement/<int:appart_id>', methods=['DELETE'])
def delete_appartement(appart_id):
    appart = Appartement.query.get_or_404(appart_id)
    db.session.delete(appart)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/locataire', methods=['POST'])
def create_locataire():
    data = request.json
    locataire = Locataire(
        nom=data['nom'],
        prenom=data['prenom'],
        email=data.get('email'),
        telephone=data.get('telephone'),
        adresse_precedente=data.get('adresse_precedente'),
        depot_garantie=Decimal(str(data.get('depot_garantie', 0))) if data.get('depot_garantie') else None,
        date_debut_bail=datetime.strptime(data['date_debut_bail'], '%Y-%m-%d').date() if data.get('date_debut_bail') else None,
        date_fin_bail=datetime.strptime(data['date_fin_bail'], '%Y-%m-%d').date() if data.get('date_fin_bail') else None,
        statut=StatutLocataire.ACTIF if data.get('statut', 'Actif') == 'Actif' else StatutLocataire.INACTIF,
        appartement_id=data.get('appartement_id')
    )
    db.session.add(locataire)
    db.session.commit()
    return jsonify({'success': True, 'id': locataire.id})

@app.route('/api/locataire/<int:locataire_id>', methods=['PUT'])
def update_locataire(locataire_id):
    locataire = Locataire.query.get_or_404(locataire_id)
    data = request.json
    if 'nom' in data:
        locataire.nom = data['nom']
    if 'prenom' in data:
        locataire.prenom = data['prenom']
    if 'email' in data:
        locataire.email = data['email']
    if 'telephone' in data:
        locataire.telephone = data['telephone']
    if 'adresse_precedente' in data:
        locataire.adresse_precedente = data['adresse_precedente']
    if 'depot_garantie' in data:
        locataire.depot_garantie = Decimal(str(data['depot_garantie'])) if data['depot_garantie'] else None
    if 'date_debut_bail' in data:
        locataire.date_debut_bail = datetime.strptime(data['date_debut_bail'], '%Y-%m-%d').date() if data['date_debut_bail'] else None
    if 'date_fin_bail' in data:
        locataire.date_fin_bail = datetime.strptime(data['date_fin_bail'], '%Y-%m-%d').date() if data['date_fin_bail'] else None
    if 'statut' in data:
        locataire.statut = StatutLocataire.ACTIF if data['statut'] == 'Actif' else StatutLocataire.INACTIF
    if 'appartement_id' in data:
        locataire.appartement_id = data['appartement_id'] if data['appartement_id'] else None
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/locataire/<int:locataire_id>', methods=['DELETE'])
def delete_locataire(locataire_id):
    locataire = Locataire.query.get_or_404(locataire_id)
    db.session.delete(locataire)
    db.session.commit()
    return jsonify({'success': True})

# Upload attestation assurance
@app.route('/api/locataire/<int:locataire_id>/assurance', methods=['POST'])
def upload_assurance(locataire_id):
    locataire = Locataire.query.get_or_404(locataire_id)

    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Aucun fichier'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Aucun fichier sélectionné'}), 400

    if file and file.filename.lower().endswith('.pdf'):
        filename = secure_filename(f"assurance_{locataire_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'assurances', filename)
        file.save(filepath)

        # Supprimer l'ancien document si existe
        old_doc = DocumentLocataire.query.filter_by(locataire_id=locataire_id, type_document='assurance').first()
        if old_doc:
            if os.path.exists(old_doc.chemin_fichier):
                os.remove(old_doc.chemin_fichier)
            db.session.delete(old_doc)

        # Créer nouveau document
        doc = DocumentLocataire(
            locataire_id=locataire_id,
            type_document='assurance',
            nom_fichier=filename,
            chemin_fichier=filepath,
            date_validite=datetime.strptime(request.form.get('date_validite'), '%Y-%m-%d').date() if request.form.get('date_validite') else None
        )
        db.session.add(doc)
        db.session.commit()

        return jsonify({'success': True, 'id': doc.id})

    return jsonify({'success': False, 'error': 'Format non supporté (PDF uniquement)'}), 400

@app.route('/api/locataire/<int:locataire_id>/assurance', methods=['GET'])
def get_assurance(locataire_id):
    doc = DocumentLocataire.query.filter_by(locataire_id=locataire_id, type_document='assurance').first()
    if doc and os.path.exists(doc.chemin_fichier):
        return send_file(doc.chemin_fichier, as_attachment=True, download_name=doc.nom_fichier)
    return jsonify({'success': False, 'error': 'Document non trouvé'}), 404


@app.route('/api/locataire/<int:locataire_id>/assurance', methods=['DELETE'])
def delete_assurance(locataire_id):
    """Supprimer l'attestation d'assurance d'un locataire"""
    try:
        doc = DocumentLocataire.query.filter_by(locataire_id=locataire_id, type_document='assurance').first()
        if doc:
            # Supprimer le fichier physique
            if os.path.exists(doc.chemin_fichier):
                os.remove(doc.chemin_fichier)
            # Supprimer l'entrée en base
            db.session.delete(doc)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Assurance supprimée'})
        return jsonify({'success': False, 'error': 'Aucune assurance trouvée'}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/locataire/<int:locataire_id>/bail', methods=['POST'])
def upload_bail(locataire_id):
    Locataire.query.get_or_404(locataire_id)

    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Aucun fichier'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Aucun fichier sélectionné'}), 400

    if file and file.filename.lower().endswith('.pdf'):
        filename = secure_filename(f"bail_{locataire_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'assurances', filename)
        file.save(filepath)

        old_doc = DocumentLocataire.query.filter_by(locataire_id=locataire_id, type_document='bail').first()
        if old_doc:
            if os.path.exists(old_doc.chemin_fichier):
                os.remove(old_doc.chemin_fichier)
            db.session.delete(old_doc)

        doc = DocumentLocataire(
            locataire_id=locataire_id,
            type_document='bail',
            nom_fichier=filename,
            chemin_fichier=filepath
        )
        db.session.add(doc)
        db.session.commit()

        return jsonify({'success': True, 'id': doc.id})

    return jsonify({'success': False, 'error': 'Format non supporté (PDF uniquement)'}), 400


@app.route('/api/locataire/<int:locataire_id>/bail', methods=['GET'])
def get_bail(locataire_id):
    doc = DocumentLocataire.query.filter_by(locataire_id=locataire_id, type_document='bail').first()
    if doc and os.path.exists(doc.chemin_fichier):
        return send_file(doc.chemin_fichier, as_attachment=True, download_name=doc.nom_fichier)
    return jsonify({'success': False, 'error': 'Bail non trouvé'}), 404


@app.route('/api/locataire/<int:locataire_id>/bail', methods=['DELETE'])
def delete_bail(locataire_id):
    """Supprimer le document de bail d'un locataire"""
    try:
        doc = DocumentLocataire.query.filter_by(locataire_id=locataire_id, type_document='bail').first()
        if doc:
            # Supprimer le fichier physique
            if os.path.exists(doc.chemin_fichier):
                os.remove(doc.chemin_fichier)
            # Supprimer l'entrée en base
            db.session.delete(doc)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Bail supprimé'})
        return jsonify({'success': False, 'error': 'Aucun bail trouvé'}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# Upload photo de locataire
@app.route('/api/locataire/<int:locataire_id>/photo', methods=['POST'])
def upload_photo(locataire_id):
    locataire = Locataire.query.get_or_404(locataire_id)

    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Aucun fichier'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Aucun fichier sélectionné'}), 400

    # Vérifier que c'est une image
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    if file and any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
        filename = secure_filename(f"photo_{locataire_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{file.filename.rsplit('.', 1)[1].lower()}")

        # Créer le dossier photos si nécessaire
        upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'photos')
        os.makedirs(upload_dir, exist_ok=True)

        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)

        # Supprimer l'ancienne photo si elle existe
        old_doc = DocumentLocataire.query.filter_by(locataire_id=locataire_id, type_document='photo').first()
        if old_doc:
            if os.path.exists(old_doc.chemin_fichier):
                os.remove(old_doc.chemin_fichier)
            db.session.delete(old_doc)

        # Créer l'enregistrement
        doc = DocumentLocataire(
            locataire_id=locataire_id,
            type_document='photo',
            nom_fichier=filename,
            chemin_fichier=filepath
        )
        db.session.add(doc)
        db.session.commit()

        return jsonify({'success': True, 'id': doc.id})

    return jsonify({'success': False, 'error': 'Format non supporté (images uniquement)'}), 400

# Récupérer photo de locataire
@app.route('/api/locataire/<int:locataire_id>/photo', methods=['GET'])
def get_photo(locataire_id):
    doc = DocumentLocataire.query.filter_by(locataire_id=locataire_id, type_document='photo').first()
    if doc and os.path.exists(doc.chemin_fichier):
        return send_file(doc.chemin_fichier, as_attachment=False)
    return jsonify({'success': False, 'error': 'Photo non trouvée'}), 404

@app.route('/api/locataire/<int:locataire_id>/etat-lieux', methods=['POST'])
def create_etat_lieux(locataire_id):
    Locataire.query.get_or_404(locataire_id)
    data = request.get_json(silent=True) or {}

    if not data.get('date_etat'):
        return jsonify({'success': False, 'error': 'Date de l\'état des lieux requise'}), 400

    raw_type = (data.get('type_etat') or '').strip().lower()
    if raw_type in ('entree', 'entrée'):
        type_etat = TypeEtatLieux.ENTREE
    elif raw_type in ('sortie',):
        type_etat = TypeEtatLieux.SORTIE
    else:
        return jsonify({'success': False, 'error': 'Type d\'état des lieux invalide'}), 400

    try:
        parsed_date = datetime.strptime(data['date_etat'], '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'success': False, 'error': 'Format de date invalide'}), 400

    # Créer l'enregistrement
    etat = EtatDesLieux(
        locataire_id=locataire_id,
        type_etat=type_etat,
        date_etat=parsed_date,
        releve_electricite=data.get('releve_electricite'),
        releve_gaz=data.get('releve_gaz'),
        releve_eau_froide=data.get('releve_eau_froide'),
        releve_eau_chaude=data.get('releve_eau_chaude'),
        observations=data.get('observations')
    )
    db.session.add(etat)
    db.session.commit()
    return jsonify({'success': True, 'id': etat.id, 'pdf_generated': False})


@app.route('/api/locataire/<int:locataire_id>/etat-lieux/prefill-pdf', methods=['POST'])
def prefill_etat_lieux_pdf(locataire_id):
    locataire = Locataire.query.get_or_404(locataire_id)

    data = request.get_json(silent=True) or {}
    raw_type = (data.get('type_etat') or 'entree').strip().lower()
    type_etat = 'entree' if raw_type in ('entree', 'entrée') else 'sortie'

    raw_date = data.get('date_etat')
    try:
        date_etat = datetime.strptime(raw_date, '%Y-%m-%d').date() if raw_date else date.today()
    except ValueError:
        return jsonify({'success': False, 'error': 'Format de date invalide'}), 400

    appartement = locataire.appartement
    bien = appartement.bien if appartement and appartement.bien else SimpleNamespace(adresse='Adresse non renseignée')
    sci = bien.sci if getattr(bien, 'sci', None) else SimpleNamespace(nom='Bailleur non renseigné', adresse=None, email=None)

    bailleur_pdf = SimpleNamespace(
        nom=(data.get('bailleur_nom') or getattr(sci, 'nom', None) or 'Bailleur non renseigné').strip(),
        adresse=(data.get('bailleur_adresse') or getattr(sci, 'adresse', None) or '').strip(),
        email=(data.get('bailleur_email') or getattr(sci, 'email', None) or '').strip(),
        representant=(data.get('bailleur_representant') or '').strip(),
        telephone=(data.get('bailleur_telephone') or '').strip()
    )

    if not appartement:
        appartement = SimpleNamespace(numero_porte='-', nb_pieces=None, etage=None, surface=None)

    # Objet temporaire pour fallback HTML si besoin.
    etat_temp = SimpleNamespace(
        type_etat=type_etat,
        date_etat=date_etat,
        releve_electricite=None,
        releve_gaz=None,
        releve_eau_froide=None,
        releve_eau_chaude=None,
        observations=data.get('observations') or ''
    )

    drafts_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'etats_lieux', 'drafts')
    os.makedirs(drafts_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    filename = secure_filename(f"prefill_etat_lieux_{type_etat}_{locataire_id}_{timestamp}.pdf")
    filepath = os.path.join(drafts_dir, filename)

    # Priorité: remplissage du PDF modèle par coordonnées (PyMuPDF).
    pdf_modele = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'etatdeslieux.pdf')
    donnees_formulaire = {
        'anchors': {
            'adresse_logement': bien.adresse if bien and getattr(bien, 'adresse', None) else '',
            'bailleur_nom': bailleur_pdf.nom,
            'bailleur_adresse': bailleur_pdf.adresse,
            'date_entree': locataire.date_debut_bail.strftime('%d/%m/%Y') if locataire.date_debut_bail else date_etat.strftime('%d/%m/%Y'),
            'date_sortie': locataire.date_fin_bail.strftime('%d/%m/%Y') if locataire.date_fin_bail else '',
            'is_entree': type_etat == 'entree',
            'locataire_nom': f"{locataire.prenom} {locataire.nom}",
            'observations': data.get('observations') or ''
        }
    }

    if os.path.exists(pdf_modele):
        success, error = remplir_etat_des_lieux_modele(pdf_modele, filepath, donnees_formulaire)
    else:
        # Fallback: génération HTML/PDF si le modèle n'est pas disponible.
        html_content = render_template(
            'pdf/etat_lieux.html',
            etat=etat_temp,
            locataire=locataire,
            appartement=appartement,
            bien=bien,
            sci=sci,
            bailleur_pdf=bailleur_pdf,
            now=datetime.now()
        )
        success, error = html_to_pdf(html_content, filepath)

    if not success:
        return jsonify({
            'success': False,
            'code': 'pdf_engine_unavailable',
            'retryable': True,
            'error': "Impossible de générer le PDF prérempli depuis le modèle.",
            'details': error
        }), 503

    historique = PrefillPdfHistorique(
        locataire_id=locataire.id,
        type_etat=type_etat,
        date_etat=date_etat,
        nom_fichier=filename,
        chemin_fichier=filepath
    )
    db.session.add(historique)
    db.session.commit()

    return jsonify({
        'success': True,
        'id': historique.id,
        'download_url': f'/api/etat-lieux/prefill/{historique.id}/download',
        'filename': filename
    })

@app.route('/api/etat-lieux/prefill/<int:prefill_id>/download', methods=['GET'])
def download_prefill_pdf(prefill_id):
    prefill = PrefillPdfHistorique.query.get_or_404(prefill_id)

    if not prefill.chemin_fichier or not os.path.exists(prefill.chemin_fichier):
        return jsonify({'success': False, 'error': 'Fichier introuvable, regénérez le PDF'}), 404

    return send_file(prefill.chemin_fichier, as_attachment=True, download_name=prefill.nom_fichier)


@app.route('/api/etat-lieux/prefill/<int:prefill_id>', methods=['DELETE'])
def delete_prefill_pdf(prefill_id):
    prefill = PrefillPdfHistorique.query.get_or_404(prefill_id)

    if prefill.chemin_fichier and os.path.exists(prefill.chemin_fichier):
        try:
            os.remove(prefill.chemin_fichier)
        except OSError:
            pass

    db.session.delete(prefill)
    db.session.commit()
    return jsonify({'success': True, 'message': 'PDF généré supprimé'})

# Génération avancée d'état des lieux avec template complet
@app.route('/api/locataire/<int:locataire_id>/etat-lieux/generate', methods=['POST'])
def generate_etat_lieux_avance(locataire_id):
    locataire = Locataire.query.get_or_404(locataire_id)
    data = request.json

    # Créer l'enregistrement
    etat = EtatDesLieux(
        locataire_id=locataire_id,
        type_etat=TypeEtatLieux.ENTREE if data['type_etat'] == 'Entrée' else TypeEtatLieux.SORTIE,
        date_etat=datetime.strptime(data['date_etat'], '%Y-%m-%d').date(),
        releve_electricite=data.get('releve_electricite'),
        releve_gaz=data.get('releve_gaz'),
        releve_eau_froide=data.get('releve_eau_froide'),
        releve_eau_chaude=data.get('releve_eau_chaude'),
        observations=data.get('observations')
    )
    db.session.add(etat)
    db.session.flush()  # Pour obtenir l'ID

    # Générer le PDF avec le template complet
    try:
        # Récupérer les données nécessaires
        appartement = locataire.appartement
        bien = appartement.bien if appartement else None
        sci = bien.sci if bien else None

        # Choisir le template selon les options
        template_name = 'pdf/etat_lieux_complet.html'
        if not data.get('format_detaille', True):
            template_name = 'pdf/etat_lieux.html'

        # Générer le HTML depuis le template
        html_content = render_template(template_name,
                                     etat=etat,
                                     locataire=locataire,
                                     appartement=appartement,
                                     bien=bien,
                                     sci=sci,
                                     now=datetime.now(),
                                     options=data)  # Passer les options au template

        # Créer le dossier de destination
        generated_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'etats_lieux', 'generated')
        os.makedirs(generated_dir, exist_ok=True)

        # Nom du fichier
        type_str = etat.type_etat.value.lower()
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        filename = f"etat_lieux_{type_str}_{locataire.nom}_{locataire.prenom}_{timestamp}.pdf"
        filepath = os.path.join(generated_dir, filename)

        # Convertir en PDF
        success, error = html_to_pdf(html_content, filepath)

        if success:
            etat.chemin_fichier = filepath
            db.session.commit()
            return jsonify({
                'success': True,
                'id': etat.id,
                'pdf_generated': True,
                'download_url': f'/api/etat-lieux/{etat.id}/download',
                'filename': filename
            })
        else:
            db.session.commit()
            return jsonify({'success': True, 'id': etat.id, 'pdf_generated': False, 'pdf_error': error})

    except Exception as e:
        db.session.commit()
        return jsonify({'success': True, 'id': etat.id, 'pdf_generated': False, 'pdf_error': str(e)})

# Aperçu HTML d'un état des lieux (sans sauvegarde)
@app.route('/api/locataire/<int:locataire_id>/etat-lieux/preview', methods=['GET'])
def preview_etat_lieux(locataire_id):
    locataire = Locataire.query.get_or_404(locataire_id)

    # Créer un objet temporaire pour l'aperçu
    class PreviewEtat:
        def __init__(self):
            self.type_etat = TypeEtatLieux.ENTREE
            self.date_etat = date.today()
            self.releve_electricite = ""
            self.releve_gaz = ""
            self.releve_eau_froide = ""
            self.releve_eau_chaude = ""
            self.observations = "Aperçu de l'état des lieux - les champs seront remplis lors de la génération finale."

    etat = PreviewEtat()

    # Récupérer les données nécessaires
    appartement = locataire.appartement
    bien = appartement.bien if appartement else None
    sci = bien.sci if bien else None

    # Générer l'HTML pour aperçu
    html_content = render_template('pdf/etat_lieux_complet.html',
                                 etat=etat,
                                 locataire=locataire,
                                 appartement=appartement,
                                 bien=bien,
                                 sci=sci,
                                 now=datetime.now())

    return html_content

# Upload état des lieux PDF
@app.route('/api/locataire/<int:locataire_id>/etat-lieux/upload', methods=['POST'])
def upload_etat_lieux(locataire_id):
    locataire = Locataire.query.get_or_404(locataire_id)

    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Aucun fichier'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Aucun fichier sélectionné'}), 400

    # Récupérer les métadonnées du formulaire
    type_etat = (request.form.get('type_etat', 'entree') or 'entree').strip().lower()  # 'entree' ou 'sortie'
    date_etat = request.form.get('date_etat')

    if not date_etat:
        return jsonify({'success': False, 'error': 'Date requise'}), 400

    if type_etat not in ('entree', 'entrée', 'sortie'):
        return jsonify({'success': False, 'error': 'Type d\'état des lieux invalide'}), 400

    try:
        parsed_date = datetime.strptime(date_etat, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'success': False, 'error': 'Format de date invalide'}), 400

    if file and file.filename.lower().endswith('.pdf'):
        # Générer nom de fichier unique
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        filename = secure_filename(f"etat_lieux_{type_etat}_{locataire_id}_{timestamp}.pdf")

        # Créer le dossier si nécessaire
        upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'etats_lieux', 'uploaded')
        os.makedirs(upload_dir, exist_ok=True)

        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)

        # Créer l'enregistrement dans la base
        etat = EtatDesLieux(
            locataire_id=locataire_id,
            type_etat=TypeEtatLieux.ENTREE if type_etat in ('entree', 'entrée') else TypeEtatLieux.SORTIE,
            date_etat=parsed_date,
            chemin_fichier=filepath
        )
        db.session.add(etat)
        db.session.commit()

        return jsonify({'success': True, 'id': etat.id, 'message': 'État des lieux uploadé avec succès'})

    return jsonify({'success': False, 'error': 'Format non supporté (PDF uniquement)'}), 400


@app.route('/api/etat-lieux/<int:etat_id>/attach-pdf', methods=['POST'])
def attach_pdf_to_etat(etat_id):
    etat = EtatDesLieux.query.get_or_404(etat_id)

    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Aucun fichier'}), 400

    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({'success': False, 'error': 'Aucun fichier sélectionné'}), 400

    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'success': False, 'error': 'Format non supporté (PDF uniquement)'}), 400

    upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'etats_lieux', 'attached')
    os.makedirs(upload_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    filename = secure_filename(f"etat_lieux_attache_{etat_id}_{timestamp}.pdf")
    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)

    if etat.chemin_fichier and os.path.exists(etat.chemin_fichier):
        try:
            os.remove(etat.chemin_fichier)
        except OSError:
            pass

    etat.chemin_fichier = filepath
    db.session.commit()

    return jsonify({'success': True, 'id': etat.id, 'message': 'PDF rattaché avec succès'})

# Lister les états des lieux d'un locataire
@app.route('/api/locataire/<int:locataire_id>/etats-lieux', methods=['GET'])
def get_etats_lieux(locataire_id):
    etats = EtatDesLieux.query.filter_by(locataire_id=locataire_id).order_by(EtatDesLieux.created_at.desc()).all()

    result = []
    for etat in etats:
        result.append({
            'id': etat.id,
            'type_etat': etat.type_etat.value,
            'date_etat': etat.date_etat.strftime('%Y-%m-%d'),
            'has_file': etat.chemin_fichier is not None,
            'created_at': etat.created_at.strftime('%d/%m/%Y à %H:%M'),
            'source': 'generated' if etat.chemin_fichier and 'generated' in etat.chemin_fichier else 'uploaded'
        })

    return jsonify(result)

# Télécharger un état des lieux
@app.route('/api/etat-lieux/<int:etat_id>/download', methods=['GET'])
def download_etat_lieux(etat_id):
    etat = EtatDesLieux.query.get_or_404(etat_id)

    if not etat.chemin_fichier or not os.path.exists(etat.chemin_fichier):
        return jsonify({'success': False, 'error': 'Fichier non trouvé'}), 404

    # Générer nom de fichier pour le téléchargement
    type_str = etat.type_etat.value.lower()
    date_str = etat.date_etat.strftime('%Y%m%d')
    locataire = etat.locataire
    nom_fichier = f"etat_lieux_{type_str}_{locataire.nom}_{date_str}.pdf"

    return send_file(etat.chemin_fichier, as_attachment=True, download_name=nom_fichier)

# Supprimer un état des lieux
@app.route('/api/etat-lieux/<int:etat_id>', methods=['DELETE'])
def delete_etat_lieux(etat_id):
    etat = EtatDesLieux.query.get_or_404(etat_id)

    # Supprimer le fichier si il existe
    if etat.chemin_fichier and os.path.exists(etat.chemin_fichier):
        try:
            os.remove(etat.chemin_fichier)
        except OSError:
            pass  # Ignore les erreurs de suppression de fichier

    # Supprimer l'enregistrement
    db.session.delete(etat)
    db.session.commit()

    return jsonify({'success': True, 'message': 'État des lieux supprimé'})

@app.route('/api/etat-lieux/<int:etat_id>/pdf')
def pdf_etat_lieux(etat_id):
    etat = EtatDesLieux.query.get_or_404(etat_id)
    locataire = etat.locataire
    appartement = locataire.appartement
    bien = appartement.bien if appartement else None
    sci = bien.sci if bien else None

    html = render_template('pdf/etat_lieux.html',
                          etat=etat,
                          locataire=locataire,
                          appartement=appartement,
                          bien=bien,
                          sci=sci,
                          mois_fr=MOIS_FR)
    return html

# ============================================
# API Photos d'états des lieux
# ============================================

# Upload de photos pour un état des lieux (multiple)
@app.route('/api/etat-lieux/<int:etat_id>/photos', methods=['POST'])
def upload_photos_etat_lieux(etat_id):
    etat = EtatDesLieux.query.get_or_404(etat_id)

    if 'files' not in request.files and 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Aucun fichier'}), 400

    # Supporter à la fois 'files' (multiple) et 'file' (single)
    files = request.files.getlist('files') or [request.files.get('file')]
    files = [f for f in files if f and f.filename]

    if not files:
        return jsonify({'success': False, 'error': 'Aucun fichier sélectionné'}), 400

    allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    uploaded = []
    errors = []

    # Créer le dossier pour cet état des lieux
    upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'etats_lieux', 'photos', str(etat_id))
    os.makedirs(upload_dir, exist_ok=True)

    descriptions = request.form.getlist('descriptions') or []

    for i, file in enumerate(files):
        if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
            errors.append(f"Format non supporté: {file.filename}")
            continue

        # Générer nom unique
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = secure_filename(f"photo_{etat_id}_{timestamp}.{ext}")
        filepath = os.path.join(upload_dir, filename)

        file.save(filepath)

        # Créer l'enregistrement
        description = descriptions[i] if i < len(descriptions) else None
        photo = PhotoEtatLieux(
            etat_lieux_id=etat_id,
            nom_fichier=filename,
            chemin_fichier=filepath,
            description=description
        )
        db.session.add(photo)
        uploaded.append({'filename': filename, 'description': description})

    db.session.commit()

    return jsonify({
        'success': len(uploaded) > 0,
        'uploaded': uploaded,
        'errors': errors,
        'count': len(uploaded)
    })

# Lister les photos d'un état des lieux
@app.route('/api/etat-lieux/<int:etat_id>/photos', methods=['GET'])
def get_photos_etat_lieux(etat_id):
    etat = EtatDesLieux.query.get_or_404(etat_id)
    photos = PhotoEtatLieux.query.filter_by(etat_lieux_id=etat_id).order_by(PhotoEtatLieux.created_at.asc()).all()

    result = []
    for photo in photos:
        result.append({
            'id': photo.id,
            'nom_fichier': photo.nom_fichier,
            'description': photo.description,
            'url': f'/api/etat-lieux/photo/{photo.id}',
            'created_at': photo.created_at.strftime('%d/%m/%Y à %H:%M')
        })

    return jsonify(result)

# Récupérer une photo spécifique
@app.route('/api/etat-lieux/photo/<int:photo_id>', methods=['GET'])
def get_photo_etat_lieux(photo_id):
    photo = PhotoEtatLieux.query.get_or_404(photo_id)

    if not os.path.exists(photo.chemin_fichier):
        return jsonify({'success': False, 'error': 'Fichier non trouvé'}), 404

    return send_file(photo.chemin_fichier, as_attachment=False)

# Supprimer une photo
@app.route('/api/etat-lieux/photo/<int:photo_id>', methods=['DELETE'])
def delete_photo_etat_lieux(photo_id):
    photo = PhotoEtatLieux.query.get_or_404(photo_id)

    # Supprimer le fichier physique
    if os.path.exists(photo.chemin_fichier):
        try:
            os.remove(photo.chemin_fichier)
        except OSError:
            pass

    # Supprimer l'enregistrement
    db.session.delete(photo)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Photo supprimée'})

# Mettre à jour la description d'une photo
@app.route('/api/etat-lieux/photo/<int:photo_id>', methods=['PUT'])
def update_photo_etat_lieux(photo_id):
    photo = PhotoEtatLieux.query.get_or_404(photo_id)
    data = request.json

    if 'description' in data:
        photo.description = data['description']

    db.session.commit()
    return jsonify({'success': True})

# Paiements
@app.route('/api/paiement', methods=['POST'])
def create_paiement():
    data = request.json
    paiement = Paiement.query.filter_by(
        locataire_id=data['locataire_id'],
        mois=data['mois'],
        annee=data['annee']
    ).first()

    nouveau_montant = Decimal(str(data['montant_paye']))

    # Si add_to_existing est True, on additionne au montant existant
    add_to_existing = data.get('add_to_existing', False)

    if paiement:
        if add_to_existing:
            # Ajouter le nouveau versement au montant existant
            paiement.montant_paye = Decimal(str(paiement.montant_paye or 0)) + nouveau_montant
        else:
            # Remplacer le montant (comportement par défaut)
            paiement.montant_paye = nouveau_montant
        paiement.date_paiement = datetime.strptime(data['date_paiement'], '%Y-%m-%d').date() if data.get('date_paiement') else paiement.date_paiement
        paiement.mode_paiement = data.get('mode_paiement') or paiement.mode_paiement
    else:
        paiement = Paiement(
            locataire_id=data['locataire_id'],
            mois=data['mois'],
            annee=data['annee'],
            montant_paye=nouveau_montant,
            date_paiement=datetime.strptime(data['date_paiement'], '%Y-%m-%d').date() if data.get('date_paiement') else None,
            mode_paiement=data.get('mode_paiement')
        )
        db.session.add(paiement)

    db.session.commit()
    return jsonify({
        'success': True,
        'id': paiement.id,
        'montant_total': float(paiement.montant_paye),
        'reste_a_payer': float(paiement.reste_a_payer)
    })

@app.route('/api/paiement/<int:paiement_id>', methods=['DELETE'])
def delete_paiement(paiement_id):
    paiement = Paiement.query.get_or_404(paiement_id)
    db.session.delete(paiement)
    db.session.commit()
    return jsonify({'success': True})

# Appels de loyer
@app.route('/api/appel-loyer', methods=['POST'])
def create_appel_loyer():
    data = request.json
    locataire = Locataire.query.get_or_404(data['locataire_id'])
    mois = int(data['mois'])
    annee = int(data['annee'])

    # Calculer les arriérés des mois précédents
    arrieres = locataire.get_arrieres(mois, annee)

    appel = AppelLoyer(
        locataire_id=data['locataire_id'],
        mois=mois,
        annee=annee,
        loyer_hc=Decimal(str(data.get('loyer_hc', locataire.loyer_actuel or 0))),
        charges=Decimal(str(data.get('charges', locataire.charges_actuelles or 0))),
        arrieres=arrieres,
        date_echeance=datetime.strptime(data['date_echeance'], '%Y-%m-%d').date() if data.get('date_echeance') else None
    )
    db.session.add(appel)
    db.session.commit()

    # Genere le PDF local en arriere-plan applicatif des la creation.
    _generate_appel_pdf_file(appel, force_regenerate=True)

    return jsonify({'success': True, 'id': appel.id, 'arrieres': float(arrieres)})

@app.route('/api/appel-loyer/<int:appel_id>/pdf')
def pdf_appel_loyer(appel_id):
    appel = AppelLoyer.query.get_or_404(appel_id)
    locataire = appel.locataire
    appartement = locataire.appartement
    bien = appartement.bien if appartement else None
    sci = bien.sci if bien else None

    html = render_template('pdf/appel_loyer.html',
                          appel=appel,
                          locataire=locataire,
                          appartement=appartement,
                          bien=bien,
                          sci=sci,
                          mois_fr=MOIS_FR)
    return html

@app.route('/api/appel-loyer/<int:appel_id>', methods=['DELETE'])
def delete_appel_loyer(appel_id):
    appel = AppelLoyer.query.get_or_404(appel_id)
    db.session.delete(appel)
    db.session.commit()
    return jsonify({'success': True})

# Quittances
@app.route('/api/quittance', methods=['POST'])
def create_quittance():
    data = request.json
    locataire = Locataire.query.get_or_404(data['locataire_id'])
    mois = int(data['mois'])
    annee = int(data['annee'])

    montant_paye = Decimal(str(data['montant_paye']))
    loyer_hc = Decimal(str(data.get('loyer_hc', locataire.loyer_actuel or 0)))
    charges = Decimal(str(data.get('charges', locataire.charges_actuelles or 0)))
    total_attendu = loyer_hc + charges
    date_paiement = datetime.strptime(data['date_paiement'], '%Y-%m-%d').date() if data.get('date_paiement') else date.today()

    # Vérifier que le montant payé couvre l'intégralité du loyer
    if montant_paye < total_attendu:
        return jsonify({
            'success': False,
            'error': f"Impossible de générer la quittance : le montant payé ({float(montant_paye):.2f} €) est inférieur au loyer dû ({float(total_attendu):.2f} €)"
        }), 400

    # Vérifier si une quittance existe déjà pour ce mois
    existing_quittance = Quittance.query.filter_by(
        locataire_id=data['locataire_id'],
        mois=mois,
        annee=annee
    ).first()

    if existing_quittance:
        return jsonify({
            'success': False,
            'error': f"Une quittance existe déjà pour {MOIS_FR[mois]} {annee}"
        }), 400

    # Créer ou mettre à jour le paiement correspondant dans le compte locatif
    paiement = Paiement.query.filter_by(
        locataire_id=data['locataire_id'],
        mois=mois,
        annee=annee
    ).first()

    if paiement:
        # Mettre à jour le paiement existant
        paiement.montant_paye = montant_paye
        paiement.date_paiement = date_paiement
        paiement.mode_paiement = data.get('mode_paiement', paiement.mode_paiement)
    else:
        # Créer un nouveau paiement
        paiement = Paiement(
            locataire_id=data['locataire_id'],
            mois=mois,
            annee=annee,
            montant_paye=montant_paye,
            date_paiement=date_paiement,
            mode_paiement=data.get('mode_paiement'),
            notes="Paiement créé via quittance"
        )
        db.session.add(paiement)

    # Créer la quittance
    quittance = Quittance(
        locataire_id=data['locataire_id'],
        mois=mois,
        annee=annee,
        loyer_hc=loyer_hc,
        charges=charges,
        montant_paye=montant_paye,
        date_paiement=date_paiement
    )
    db.session.add(quittance)
    db.session.commit()

    # Genere le PDF local en arriere-plan applicatif des la creation.
    _generate_quittance_pdf_file(quittance, force_regenerate=True)

    return jsonify({
        'success': True,
        'id': quittance.id,
        'paiement_id': paiement.id,
        'message': 'Quittance créée et paiement enregistré dans le compte locatif'
    })

@app.route('/api/quittance/<int:quittance_id>/pdf')
def pdf_quittance(quittance_id):
    quittance = Quittance.query.get_or_404(quittance_id)
    locataire = quittance.locataire
    appartement = locataire.appartement
    bien = appartement.bien if appartement else None
    sci = bien.sci if bien else None

    html = render_template('pdf/quittance.html',
                          quittance=quittance,
                          locataire=locataire,
                          appartement=appartement,
                          bien=bien,
                          sci=sci,
                          mois_fr=MOIS_FR)
    return html

@app.route('/api/quittance/<int:quittance_id>', methods=['DELETE'])
def delete_quittance(quittance_id):
    quittance = Quittance.query.get_or_404(quittance_id)
    db.session.delete(quittance)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/quittance/<int:quittance_id>/envoyer', methods=['POST'])
def envoyer_quittance_email(quittance_id):
    """Envoyer une quittance par email au locataire"""
    data = request.get_json(silent=True) or {}
    quittance = Quittance.query.get_or_404(quittance_id)
    locataire = quittance.locataire
    config = ConfigEmail.query.first()

    if not config:
        return jsonify({'success': False, 'error': 'Configuration email non définie'}), 400

    if not locataire.email:
        return jsonify({'success': False, 'error': 'Le locataire n\'a pas d\'adresse email'}), 400

    appartement = locataire.appartement
    bien = appartement.bien if appartement else None
    sci = bien.sci if bien else None

    # Toujours régénérer le PDF pour utiliser le template actuel
    pdf_path, pdf_error = _generate_quittance_pdf_file(quittance, force_regenerate=True)
    if not pdf_path:
        return jsonify({'success': False, 'error': f'Erreur génération PDF: {pdf_error}'}), 500

    modele_email = (data.get('modele_email') or 'standard').strip().lower()
    sujet, corps = _build_email_quittance(locataire, quittance, sci=sci, modele_email=modele_email)
    if (data.get('sujet') or '').strip():
        sujet = data.get('sujet').strip()
    if (data.get('corps') or '').strip():
        corps = data.get('corps').strip()

    # Envoyer l'email
    success, message = envoyer_email(
        config.email_expediteur,
        config.mot_de_passe,
        locataire.email,
        sujet,
        corps,
        piece_jointe=pdf_path,
        serveur=config.serveur_smtp,
        port=config.port_smtp,
        use_tls=bool(config.use_tls)
    )

    # On garde le fichier local pour les prochains envois.

    if success:
        return jsonify({'success': True, 'message': 'Quittance envoyée par email'})
    else:
        return jsonify({'success': False, 'error': message}), 500

# Configuration email
@app.route('/api/config-email', methods=['POST'])
def save_config_email():
    data = request.json
    config = ConfigEmail.query.first()

    email_expediteur = data.get('email_expediteur') or data.get('email_address')
    mot_de_passe = data.get('mot_de_passe') or data.get('email_password')
    serveur_smtp = data.get('serveur_smtp') or data.get('smtp_server') or 'smtp.gmail.com'
    port_smtp = int(data.get('port_smtp') or data.get('smtp_port') or 587)

    if not email_expediteur or not mot_de_passe:
        return jsonify({'success': False, 'message': 'Email expéditeur et mot de passe obligatoires'}), 400

    if config:
        config.email_expediteur = email_expediteur
        config.mot_de_passe = mot_de_passe
        config.serveur_smtp = serveur_smtp
        config.port_smtp = port_smtp
        config.use_tls = data.get('use_tls', True)
    else:
        config = ConfigEmail(
            email_expediteur=email_expediteur,
            mot_de_passe=mot_de_passe,
            serveur_smtp=serveur_smtp,
            port_smtp=port_smtp,
            use_tls=data.get('use_tls', True)
        )
        db.session.add(config)

    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/test-email', methods=['POST'])
def test_email():
    try:
        data = request.get_json(silent=True) or {}

        email_expediteur = data.get('email_expediteur') or data.get('email_address')
        mot_de_passe = data.get('mot_de_passe') or data.get('email_password')
        serveur_smtp = data.get('serveur_smtp') or data.get('smtp_server') or 'smtp.gmail.com'
        email_test = data.get('email_test') or email_expediteur

        port_value = data.get('port_smtp') or data.get('smtp_port') or 587
        try:
            port_smtp = int(port_value)
        except (TypeError, ValueError):
            return jsonify({'success': False, 'message': f'Port SMTP invalide: {port_value}'}), 400

        use_tls_raw = data.get('use_tls', True)
        if isinstance(use_tls_raw, str):
            use_tls = use_tls_raw.strip().lower() in ('1', 'true', 'yes', 'on')
        else:
            use_tls = bool(use_tls_raw)

        if not email_expediteur or not mot_de_passe:
            return jsonify({'success': False, 'message': 'Email expéditeur et mot de passe obligatoires'}), 400

        success, message = envoyer_email(
            email_expediteur,
            mot_de_passe,
            email_test,
            "Test de configuration email - GestLoc",
            "<p>Test réussi !</p><p>Votre configuration email fonctionne correctement.</p>",
            serveur=serveur_smtp,
            port=port_smtp,
            use_tls=use_tls
        )

        if success:
            return jsonify({'success': True, 'message': message}), 200
        return jsonify({'success': False, 'message': message}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur interne test email: {str(e)}'}), 500

# Programmation des appels de loyer
@app.route('/api/programmation-appel', methods=['POST'])
def create_programmation_appel():
    data = request.json

    locataires_ids = data.get('locataires_ids', [])
    if isinstance(locataires_ids, list):
        locataires_ids_json = json.dumps(locataires_ids)
    else:
        locataires_ids_json = json.dumps([])

    # Parser la date et l'heure
    date_envoi_str = data['date_envoi']
    heure_envoi = data.get('heure_envoi', '09:00')
    date_envoi = datetime.strptime(f"{date_envoi_str} {heure_envoi}", '%Y-%m-%d %H:%M')

    prog = ProgrammationAppel(
        mois=int(data['mois']),
        annee=int(data['annee']),
        date_envoi=date_envoi,
        tous_locataires=data.get('tous_locataires', False),
        locataires_ids=locataires_ids_json,
        recurrent=data.get('recurrent', False),
        email_expediteur=data.get('email_expediteur'),
        statut='en_attente'
    )
    db.session.add(prog)
    db.session.commit()
    return jsonify({'success': True, 'id': prog.id})

@app.route('/api/programmation-appel/<int:prog_id>', methods=['DELETE'])
def delete_programmation_appel(prog_id):
    prog = ProgrammationAppel.query.get_or_404(prog_id)
    db.session.delete(prog)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/programmation-appel/<int:prog_id>/send', methods=['POST'])
def send_programmation_now(prog_id):
    prog = ProgrammationAppel.query.get_or_404(prog_id)
    locataires = prog.get_locataires()
    config = ConfigEmail.query.first()

    if not config:
        return jsonify({'success': False, 'message': 'Configuration email non définie'}), 400

    if not locataires:
        return jsonify({'success': False, 'message': 'Aucun locataire trouvé pour cette programmation'}), 400

    # Utiliser le mois/année de la programmation
    mois = prog.mois
    annee = prog.annee

    resultats = []
    echecs = []

    for locataire in locataires:
        if not locataire.email:
            echecs.append(f"Pas d'email pour {locataire.nom_complet}")
            continue

        if not locataire.appartement:
            echecs.append(f"Pas d'appartement pour {locataire.nom_complet}")
            continue

        # Créer ou récupérer l'appel de loyer pour ce locataire
        appel = AppelLoyer.query.filter_by(
            locataire_id=locataire.id,
            mois=mois,
            annee=annee
        ).first()

        if not appel:
            # Calculer les arriérés pour ce locataire
            arrieres = locataire.get_arrieres(mois, annee)
            appel = AppelLoyer(
                locataire_id=locataire.id,
                mois=mois,
                annee=annee,
                loyer_hc=locataire.loyer_actuel or Decimal('0.00'),
                charges=locataire.charges_actuelles or Decimal('0.00'),
                arrieres=arrieres,
                date_echeance=date(annee, mois, 5)
            )
            db.session.add(appel)
            db.session.commit()

        # Générer le PDF avec le template (toujours régénérer pour utiliser le template actuel)
        pdf_path, pdf_error = _generate_appel_pdf_file(appel, force_regenerate=True)
        if not pdf_path:
            echecs.append(f"Erreur PDF pour {locataire.nom_complet}: {pdf_error}")
            continue

        # Récupérer les infos pour l'email
        appartement = locataire.appartement
        bien = appartement.bien if appartement else None
        sci = bien.sci if bien else None

        # Utiliser le builder d'email standard
        sujet, corps = _build_email_appel(locataire, appel, sci=sci, modele_email='standard')

        # Envoyer l'email avec le PDF en pièce jointe
        success, message = envoyer_email(
            prog.email_expediteur or config.email_expediteur,
            config.mot_de_passe,
            locataire.email,
            sujet,
            corps,
            piece_jointe=pdf_path,
            serveur=config.serveur_smtp,
            port=config.port_smtp,
            use_tls=bool(config.use_tls)
        )

        if success:
            resultats.append(f"Email envoyé à {locataire.nom_complet}")
        else:
            echecs.append(f"Erreur pour {locataire.nom_complet}: {message}")

    # Mettre à jour le statut de la programmation
    if echecs and not resultats:
        prog.statut = 'erreur'
        message_final = f"Tous les envois ont échoué: {'; '.join(echecs)}"
    elif echecs:
        prog.statut = 'partiel'
        message_final = f"Envois partiels. Succès: {len(resultats)}, Échecs: {len(echecs)}"
    else:
        prog.statut = 'envoye'
        message_final = f"Tous les emails envoyés avec succès ({len(resultats)} destinataires)"

    prog.date_envoi = datetime.now()
    db.session.commit()

    return jsonify({
        'success': len(resultats) > 0,
        'message': message_final,
        'details': {
            'succes': resultats,
            'echecs': echecs
        }
    })

# Envoyer appel par email
@app.route('/api/appel-loyer/<int:appel_id>/envoyer', methods=['POST'])
def envoyer_appel_email(appel_id):
    data = request.get_json(silent=True) or {}
    appel = AppelLoyer.query.get_or_404(appel_id)
    locataire = appel.locataire
    config = ConfigEmail.query.first()

    if not config:
        return jsonify({'success': False, 'error': 'Configuration email non définie'}), 400

    if not locataire.email:
        return jsonify({'success': False, 'error': 'Le locataire n\'a pas d\'adresse email'}), 400

    # Générer le contenu de l'email
    appartement = locataire.appartement
    bien = appartement.bien if appartement else None
    sci = bien.sci if bien else None

    # Toujours régénérer le PDF pour utiliser le template actuel
    pdf_path, pdf_error = _generate_appel_pdf_file(appel, force_regenerate=True)
    if not pdf_path:
        return jsonify({'success': False, 'error': f'Erreur génération PDF: {pdf_error}'}), 500

    modele_email = (data.get('modele_email') or 'standard').strip().lower()
    sujet, corps = _build_email_appel(locataire, appel, sci=sci, modele_email=modele_email)
    if (data.get('sujet') or '').strip():
        sujet = data.get('sujet').strip()
    if (data.get('corps') or '').strip():
        corps = data.get('corps').strip()

    success, message = envoyer_email(
        config.email_expediteur,
        config.mot_de_passe,
        locataire.email,
        sujet,
        corps,
        piece_jointe=pdf_path,
        serveur=config.serveur_smtp,
        port=config.port_smtp,
        use_tls=bool(config.use_tls)
    )

    # On garde le fichier local pour les prochains envois.

    if success:
        return jsonify({'success': True, 'message': 'Appel de loyer envoyé par email'})
    return jsonify({'success': False, 'error': message}), 500

# Generate all appels for current month
@app.route('/api/generate-all-appels', methods=['POST'])
def generate_all_appels():
    locataires = Locataire.query.filter_by(statut=StatutLocataire.ACTIF).all()
    mois = date.today().month
    annee = date.today().year
    count = 0
    created_appels = []

    for loc in locataires:
        if loc.appartement:
            existing = AppelLoyer.query.filter_by(
                locataire_id=loc.id,
                mois=mois,
                annee=annee
            ).first()

            if not existing:
                # Calculer les arriérés des mois précédents
                arrieres = loc.get_arrieres(mois, annee)

                appel = AppelLoyer(
                    locataire_id=loc.id,
                    mois=mois,
                    annee=annee,
                    loyer_hc=loc.loyer_actuel or Decimal('0.00'),
                    charges=loc.charges_actuelles or Decimal('0.00'),
                    arrieres=arrieres,
                    date_echeance=date(annee, mois, 5)
                )
                db.session.add(appel)
                created_appels.append(appel)
                count += 1

    db.session.commit()

    for appel in created_appels:
        _generate_appel_pdf_file(appel, force_regenerate=True)

    return jsonify({'success': True, 'count': count})

# Generate all quittances for payments received
@app.route('/api/generate-all-quittances', methods=['POST'])
def generate_all_quittances():
    locataires = Locataire.query.filter_by(statut=StatutLocataire.ACTIF).all()
    mois = date.today().month
    annee = date.today().year
    count = 0
    created_quittances = []

    for loc in locataires:
        if loc.appartement:
            paiement = loc.get_paiement_mois(mois, annee)
            if paiement and Decimal(str(paiement.montant_paye)) >= loc.total_mensuel:
                existing = Quittance.query.filter_by(
                    locataire_id=loc.id,
                    mois=mois,
                    annee=annee
                ).first()

                if not existing:
                    quittance = Quittance(
                        locataire_id=loc.id,
                        mois=mois,
                        annee=annee,
                        loyer_hc=loc.loyer_actuel or Decimal('0.00'),
                        charges=loc.charges_actuelles or Decimal('0.00'),
                        montant_paye=paiement.montant_paye,
                        date_paiement=paiement.date_paiement
                    )
                    db.session.add(quittance)
                    created_quittances.append(quittance)
                    count += 1

    db.session.commit()

    for quittance in created_quittances:
        _generate_quittance_pdf_file(quittance, force_regenerate=True)

    return jsonify({'success': True, 'count': count})

@app.route('/api/stats')
def get_stats():
    scis = SCI.query.all()
    stats = []
    for sci in scis:
        stats.append({
            'id': sci.id,
            'nom': sci.nom,
            'total_attendu': float(sci.total_attendu),
            'total_encaisse': float(sci.total_encaisse),
            'taux': float(sci.taux_encaissement)
        })
    return jsonify(stats)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
