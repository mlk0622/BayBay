from flask_sqlalchemy import SQLAlchemy
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from datetime import datetime, date

db = SQLAlchemy()

class StatutPaiement(Enum):
    PAYE = "Payé"
    PARTIEL = "Partiel"
    IMPAYE = "Impayé"

class StatutLocataire(Enum):
    ACTIF = "Actif"
    INACTIF = "Inactif"

class TypeEtatLieux(Enum):
    ENTREE = "Entrée"
    SORTIE = "Sortie"

class SCI(db.Model):
    __tablename__ = 'sci'

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(200), nullable=False)
    ville = db.Column(db.String(100), nullable=False)
    siret = db.Column(db.String(14), nullable=True)
    adresse = db.Column(db.String(300), nullable=True)
    code_postal = db.Column(db.String(10), nullable=True)
    email = db.Column(db.String(200), nullable=True)  # Email de la SCI pour envoi

    biens = db.relationship('BienImmobilier', backref='sci', lazy=True, cascade='all, delete-orphan')

    @property
    def adresse_complete(self):
        parts = []
        if self.adresse:
            parts.append(self.adresse)
        if self.code_postal:
            parts.append(self.code_postal)
        if self.ville:
            parts.append(self.ville)
        return ', '.join(parts) if parts else ''

    @property
    def total_attendu(self):
        total = Decimal('0.00')
        for bien in self.biens:
            total += bien.total_attendu
        return total

    @property
    def total_encaisse(self):
        total = Decimal('0.00')
        for bien in self.biens:
            total += bien.total_encaisse
        return total

    @property
    def reste_a_percevoir(self):
        return self.total_attendu - self.total_encaisse

    @property
    def taux_encaissement(self):
        if self.total_attendu == 0:
            return Decimal('100.00')
        return ((self.total_encaisse / self.total_attendu) * 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

class BienImmobilier(db.Model):
    __tablename__ = 'bien_immobilier'

    id = db.Column(db.Integer, primary_key=True)
    adresse = db.Column(db.String(300), nullable=False)
    code_postal = db.Column(db.String(10), nullable=True)
    ville = db.Column(db.String(100), nullable=True)
    type_bien = db.Column(db.String(50), nullable=False)
    sci_id = db.Column(db.Integer, db.ForeignKey('sci.id'), nullable=False)

    appartements = db.relationship('Appartement', backref='bien', lazy=True, cascade='all, delete-orphan')

    @property
    def total_attendu(self):
        total = Decimal('0.00')
        for appart in self.appartements:
            if appart.locataire_actif:
                total += Decimal(str(appart.loyer_mensuel or 0)) + Decimal(str(appart.charges or 0))
        return total

    @property
    def total_encaisse(self):
        total = Decimal('0.00')
        for appart in self.appartements:
            if appart.locataire_actif:
                for paiement in appart.locataire_actif.paiements:
                    if paiement.mois == date.today().month and paiement.annee == date.today().year:
                        total += Decimal(str(paiement.montant_paye))
        return total

    @property
    def reste_a_percevoir(self):
        return self.total_attendu - self.total_encaisse

    @property
    def adresse_complete(self):
        parts = [self.adresse]
        if self.code_postal:
            parts.append(self.code_postal)
        if self.ville:
            parts.append(self.ville)
        return ', '.join(parts)

class Appartement(db.Model):
    __tablename__ = 'appartement'

    id = db.Column(db.Integer, primary_key=True)
    numero_porte = db.Column(db.String(20), nullable=False)
    type_appartement = db.Column(db.String(20), nullable=False)
    surface = db.Column(db.Numeric(10, 2), nullable=True)
    loyer_mensuel = db.Column(db.Numeric(10, 2), nullable=True)
    charges = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    nb_pieces = db.Column(db.Integer, nullable=True)
    etage = db.Column(db.String(20), nullable=True)
    bien_id = db.Column(db.Integer, db.ForeignKey('bien_immobilier.id'), nullable=False)

    locataires = db.relationship('Locataire', backref='appartement', lazy=True)

    @property
    def locataire_actif(self):
        for loc in self.locataires:
            if loc.statut == StatutLocataire.ACTIF:
                return loc
        return None

    @property
    def total_loyer(self):
        return Decimal(str(self.loyer_mensuel or 0)) + Decimal(str(self.charges or 0))

class Locataire(db.Model):
    __tablename__ = 'locataire'

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(200), nullable=True)
    telephone = db.Column(db.String(20), nullable=True)
    adresse_precedente = db.Column(db.String(300), nullable=True)
    depot_garantie = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    date_debut_bail = db.Column(db.Date, nullable=True)
    date_fin_bail = db.Column(db.Date, nullable=True)
    statut = db.Column(db.Enum(StatutLocataire), default=StatutLocataire.ACTIF)
    appartement_id = db.Column(db.Integer, db.ForeignKey('appartement.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    paiements = db.relationship('Paiement', backref='locataire', lazy=True, cascade='all, delete-orphan')
    documents = db.relationship('DocumentLocataire', backref='locataire', lazy=True, cascade='all, delete-orphan')
    etats_lieux = db.relationship('EtatDesLieux', backref='locataire', lazy=True, cascade='all, delete-orphan')

    @property
    def nom_complet(self):
        return f"{self.prenom} {self.nom}"

    @property
    def loyer_actuel(self):
        if self.appartement:
            return self.appartement.loyer_mensuel
        return Decimal('0.00')

    @property
    def charges_actuelles(self):
        if self.appartement:
            return self.appartement.charges
        return Decimal('0.00')

    @property
    def total_mensuel(self):
        return Decimal(str(self.loyer_actuel or 0)) + Decimal(str(self.charges_actuelles or 0))

    def get_paiement_mois(self, mois, annee):
        for p in self.paiements:
            if p.mois == mois and p.annee == annee:
                return p
        return None

    def get_solde_mois(self, mois, annee):
        paiement = self.get_paiement_mois(mois, annee)
        if paiement:
            return self.total_mensuel - Decimal(str(paiement.montant_paye))
        return self.total_mensuel

    def get_arrieres(self, mois, annee):
        """
        Calcule le total des arriérés (impayés) des mois précédents.
        Retourne la somme des loyers non payés ou partiellement payés avant le mois/année donné.
        Inclut les mois sans paiement enregistré depuis le début du bail.
        """
        from datetime import date as date_class

        total_arrieres = Decimal('0.00')

        if not self.date_debut_bail:
            # Sans date de début, on ne compte que les paiements existants
            for paiement in self.paiements:
                if (paiement.annee < annee) or (paiement.annee == annee and paiement.mois < mois):
                    reste = paiement.reste_a_payer
                    if reste > 0:
                        total_arrieres += reste
            return total_arrieres

        # Avec date de début, on compte tous les mois depuis le début du bail
        debut_mois = self.date_debut_bail.month
        debut_annee = self.date_debut_bail.year

        mois_courant = debut_mois
        annee_courante = debut_annee

        while (annee_courante < annee) or (annee_courante == annee and mois_courant < mois):
            paiement = self.get_paiement_mois(mois_courant, annee_courante)
            if paiement:
                reste = paiement.reste_a_payer
                if reste > 0:
                    total_arrieres += reste
            else:
                # Pas de paiement = mois entier impayé
                total_arrieres += self.total_mensuel

            mois_courant += 1
            if mois_courant > 12:
                mois_courant = 1
                annee_courante += 1

        return total_arrieres

    def est_a_jour(self, mois, annee):
        """
        Vérifie si le locataire a payé intégralement le loyer du mois/année donné.
        Retourne True si payé intégralement, False sinon.
        """
        paiement = self.get_paiement_mois(mois, annee)
        if not paiement:
            return False
        return Decimal(str(paiement.montant_paye)) >= self.total_mensuel

    def get_quittance_mois(self, mois, annee):
        """Retourne la quittance pour un mois/année donné"""
        for q in self.quittances:
            if q.mois == mois and q.annee == annee:
                return q
        return None

    def get_historique_complet(self):
        """
        Génère l'historique complet du compte locatif depuis le début du bail.
        Inclut tous les mois même sans paiement, et les quittances associées.
        Inclut également les arriérés (impayés des mois précédents) pour chaque mois.
        """
        from datetime import date as date_class

        historique = []

        if not self.date_debut_bail:
            # Si pas de date de début, on prend juste les paiements existants
            for p in self.paiements:
                quittance = self.get_quittance_mois(p.mois, p.annee)
                arrieres = self.get_arrieres(p.mois, p.annee)
                historique.append({
                    'mois': p.mois,
                    'annee': p.annee,
                    'loyer': p.loyer_attendu,
                    'charges': p.charges_attendues,
                    'total': p.total_attendu,
                    'paye': p.montant_paye,
                    'reste': p.reste_a_payer,
                    'date_paiement': p.date_paiement,
                    'statut': p.statut.value,
                    'paiement_id': p.id,
                    'quittance': quittance,
                    'solde_cumule': Decimal('0.00'),
                    'arrieres_avant': arrieres
                })
            # Tri par date décroissante
            historique.sort(key=lambda x: (x['annee'], x['mois']), reverse=True)
            return historique

        # Déterminer la période
        debut_mois = self.date_debut_bail.month
        debut_annee = self.date_debut_bail.year

        aujourd_hui = date_class.today()
        fin_mois = aujourd_hui.month
        fin_annee = aujourd_hui.year

        # Si le locataire est inactif et a une date de fin, on s'arrête là
        if self.statut == StatutLocataire.INACTIF and self.date_fin_bail:
            fin_mois = self.date_fin_bail.month
            fin_annee = self.date_fin_bail.year

        # Générer tous les mois
        mois_courant = debut_mois
        annee_courante = debut_annee

        while (annee_courante < fin_annee) or (annee_courante == fin_annee and mois_courant <= fin_mois):
            paiement = self.get_paiement_mois(mois_courant, annee_courante)
            quittance = self.get_quittance_mois(mois_courant, annee_courante)
            # Calculer les arriérés des mois précédents pour ce mois
            arrieres = self.get_arrieres(mois_courant, annee_courante)

            if paiement:
                historique.append({
                    'mois': mois_courant,
                    'annee': annee_courante,
                    'loyer': paiement.loyer_attendu,
                    'charges': paiement.charges_attendues,
                    'total': paiement.total_attendu,
                    'paye': paiement.montant_paye,
                    'reste': paiement.reste_a_payer,
                    'date_paiement': paiement.date_paiement,
                    'statut': paiement.statut.value,
                    'paiement_id': paiement.id,
                    'quittance': quittance,
                    'solde_cumule': Decimal('0.00'),
                    'arrieres_avant': arrieres
                })
            else:
                # Pas de paiement pour ce mois
                historique.append({
                    'mois': mois_courant,
                    'annee': annee_courante,
                    'loyer': self.loyer_actuel,
                    'charges': self.charges_actuelles,
                    'total': self.total_mensuel,
                    'paye': Decimal('0.00'),
                    'reste': self.total_mensuel,
                    'date_paiement': None,
                    'statut': 'Impayé',
                    'paiement_id': None,
                    'quittance': quittance,
                    'solde_cumule': Decimal('0.00'),
                    'arrieres_avant': arrieres
                })

            # Passer au mois suivant
            mois_courant += 1
            if mois_courant > 12:
                mois_courant = 1
                annee_courante += 1

        # Calculer le solde cumulé (du plus ancien au plus récent)
        historique.sort(key=lambda x: (x['annee'], x['mois']))
        solde = Decimal('0.00')
        for h in historique:
            solde += h['reste']
            h['solde_cumule'] = solde

        # Retourner en ordre décroissant (plus récent en premier)
        historique.reverse()

        return historique

    @property
    def solde_total(self):
        """Calcule le solde total (somme de tous les impayés)"""
        total = Decimal('0.00')
        for h in self.get_historique_complet():
            total += h['reste']
        return total

    @property
    def attestation_assurance(self):
        for doc in self.documents:
            if doc.type_document == 'assurance':
                return doc
        return None

class DocumentLocataire(db.Model):
    __tablename__ = 'document_locataire'

    id = db.Column(db.Integer, primary_key=True)
    locataire_id = db.Column(db.Integer, db.ForeignKey('locataire.id'), nullable=False)
    type_document = db.Column(db.String(50), nullable=False)  # 'assurance', 'identite', 'autre'
    nom_fichier = db.Column(db.String(255), nullable=False)
    chemin_fichier = db.Column(db.String(500), nullable=False)
    date_validite = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class EtatDesLieux(db.Model):
    __tablename__ = 'etat_des_lieux'

    id = db.Column(db.Integer, primary_key=True)
    locataire_id = db.Column(db.Integer, db.ForeignKey('locataire.id'), nullable=False)
    type_etat = db.Column(db.Enum(TypeEtatLieux), nullable=False)
    date_etat = db.Column(db.Date, nullable=False)
    chemin_fichier = db.Column(db.String(500), nullable=True)  # PDF généré

    # Relevés compteurs
    releve_electricite = db.Column(db.String(50), nullable=True)
    releve_gaz = db.Column(db.String(50), nullable=True)
    releve_eau_froide = db.Column(db.String(50), nullable=True)
    releve_eau_chaude = db.Column(db.String(50), nullable=True)

    # Observations
    observations = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relation avec les photos
    photos = db.relationship('PhotoEtatLieux', backref='etat_lieux', lazy=True, cascade='all, delete-orphan')


class PhotoEtatLieux(db.Model):
    """Photos attachées à un état des lieux"""
    __tablename__ = 'photo_etat_lieux'

    id = db.Column(db.Integer, primary_key=True)
    etat_lieux_id = db.Column(db.Integer, db.ForeignKey('etat_des_lieux.id'), nullable=False)
    nom_fichier = db.Column(db.String(255), nullable=False)
    chemin_fichier = db.Column(db.String(500), nullable=False)
    description = db.Column(db.String(255), nullable=True)  # Description optionnelle de la photo
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Paiement(db.Model):
    __tablename__ = 'paiement'

    id = db.Column(db.Integer, primary_key=True)
    locataire_id = db.Column(db.Integer, db.ForeignKey('locataire.id'), nullable=False)
    mois = db.Column(db.Integer, nullable=False)
    annee = db.Column(db.Integer, nullable=False)
    montant_paye = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    date_paiement = db.Column(db.Date, nullable=True)
    mode_paiement = db.Column(db.String(50), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def loyer_attendu(self):
        if self.locataire and self.locataire.appartement:
            return self.locataire.appartement.loyer_mensuel
        return Decimal('0.00')

    @property
    def charges_attendues(self):
        if self.locataire and self.locataire.appartement:
            return self.locataire.appartement.charges
        return Decimal('0.00')

    @property
    def total_attendu(self):
        return Decimal(str(self.loyer_attendu or 0)) + Decimal(str(self.charges_attendues or 0))

    @property
    def reste_a_payer(self):
        return self.total_attendu - Decimal(str(self.montant_paye))

    @property
    def statut(self):
        reste = self.reste_a_payer
        if reste <= 0:
            return StatutPaiement.PAYE
        elif Decimal(str(self.montant_paye)) > 0:
            return StatutPaiement.PARTIEL
        else:
            return StatutPaiement.IMPAYE

class AppelLoyer(db.Model):
    __tablename__ = 'appel_loyer'

    id = db.Column(db.Integer, primary_key=True)
    locataire_id = db.Column(db.Integer, db.ForeignKey('locataire.id'), nullable=False)
    mois = db.Column(db.Integer, nullable=False)
    annee = db.Column(db.Integer, nullable=False)
    loyer_hc = db.Column(db.Numeric(10, 2), nullable=False)
    charges = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    arrieres = db.Column(db.Numeric(10, 2), nullable=False, default=0)  # Arriérés des mois précédents
    date_emission = db.Column(db.Date, default=date.today)
    date_echeance = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    locataire = db.relationship('Locataire', backref='appels_loyer')

    @property
    def total(self):
        return Decimal(str(self.loyer_hc)) + Decimal(str(self.charges))

    @property
    def total_avec_arrieres(self):
        """Total incluant les arriérés des mois précédents"""
        return self.total + Decimal(str(self.arrieres or 0))

class Quittance(db.Model):
    __tablename__ = 'quittance'

    id = db.Column(db.Integer, primary_key=True)
    locataire_id = db.Column(db.Integer, db.ForeignKey('locataire.id'), nullable=False)
    mois = db.Column(db.Integer, nullable=False)
    annee = db.Column(db.Integer, nullable=False)
    loyer_hc = db.Column(db.Numeric(10, 2), nullable=False)
    charges = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    montant_paye = db.Column(db.Numeric(10, 2), nullable=False)
    date_paiement = db.Column(db.Date, nullable=True)
    date_emission = db.Column(db.Date, default=date.today)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    locataire = db.relationship('Locataire', backref='quittances')

    @property
    def total(self):
        return Decimal(str(self.loyer_hc)) + Decimal(str(self.charges))

class ConfigEmail(db.Model):
    __tablename__ = 'config_email'

    id = db.Column(db.Integer, primary_key=True)
    email_expediteur = db.Column(db.String(200), nullable=False)
    mot_de_passe = db.Column(db.String(200), nullable=False)  # Crypté en prod
    serveur_smtp = db.Column(db.String(100), nullable=False, default='smtp.gmail.com')
    port_smtp = db.Column(db.Integer, nullable=False, default=587)
    use_tls = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ProgrammationAppel(db.Model):
    __tablename__ = 'programmation_appel'

    id = db.Column(db.Integer, primary_key=True)
    mois = db.Column(db.Integer, nullable=False)
    annee = db.Column(db.Integer, nullable=False)
    date_envoi = db.Column(db.DateTime, nullable=False)  # Date et heure d'envoi
    tous_locataires = db.Column(db.Boolean, default=False)
    locataires_ids = db.Column(db.Text, nullable=True)  # JSON array of IDs
    recurrent = db.Column(db.Boolean, default=False)
    statut = db.Column(db.String(20), default='en_attente')  # 'en_attente', 'envoye', 'erreur'
    email_expediteur = db.Column(db.String(200), nullable=True)  # Email depuis lequel envoyer
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_locataires(self):
        """Résout la liste des locataires selon la configuration"""
        if self.tous_locataires:
            return Locataire.query.filter_by(statut=StatutLocataire.ACTIF).all()
        if self.locataires_ids:
            import json
            try:
                ids = json.loads(self.locataires_ids)
                return Locataire.query.filter(Locataire.id.in_(ids)).all()
            except:
                return []
        return []

    def get_description_cibles(self):
        """Retourne description lisible des cibles"""
        if self.tous_locataires:
            return "Tous les locataires actifs"
        if self.locataires_ids:
            locataires = self.get_locataires()
            if len(locataires) == 1:
                return f"{locataires[0].nom_complet}"
            return f"{len(locataires)} locataires sélectionnés"
        return "Aucun destinataire"

    @property
    def locataires_count(self):
        if self.tous_locataires:
            return Locataire.query.filter_by(statut=StatutLocataire.ACTIF).count()
        if self.locataires_ids:
            import json
            try:
                ids = json.loads(self.locataires_ids)
                return len(ids)
            except:
                return 0
        return 0


class PrefillPdfHistorique(db.Model):
    __tablename__ = 'prefill_pdf_historique'

    id = db.Column(db.Integer, primary_key=True)
    locataire_id = db.Column(db.Integer, db.ForeignKey('locataire.id'), nullable=False)
    type_etat = db.Column(db.String(20), nullable=False)  # entree / sortie
    date_etat = db.Column(db.Date, nullable=False)
    nom_fichier = db.Column(db.String(255), nullable=False)
    chemin_fichier = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    locataire = db.relationship('Locataire', backref='prefill_pdfs')

