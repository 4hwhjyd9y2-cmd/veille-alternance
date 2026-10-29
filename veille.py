#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Veille d'offres d'alternance niveau ingenieur, Nantes et proche peripherie.

Fonctionnement
  1. telecharge les pages de liste "alternance <employeur> en Loire-Atlantique"
  2. en extrait les references d'annonces, par la forme des URLs
  3. ouvre chaque annonce jamais vue et lit son bloc de donnees structurees
     JobPosting (le meme que celui lu par Google), ce qui rend le script
     insensible aux changements de mise en page
  4. applique les filtres : employeur, contrat, commune, niveau, domaine
  5. envoie un mail, met a jour etat.json et offres.json

Usage
  python veille.py            passage normal
  python veille.py --test     aucun mail envoye, le mail est affiche
  python veille.py --reset    oublie toutes les annonces deja vues
"""

import configparser
import html as _html
import json
import os
import re
import smtplib
import sys
import time
import unicodedata
import urllib.robotparser
from datetime import datetime, timedelta, timezone
try:
    from zoneinfo import ZoneInfo
    PARIS = ZoneInfo("Europe/Paris")
except Exception:          # Python trop ancien : on retombe sur l'UTC
    PARIS = timezone.utc
from email.message import EmailMessage
from urllib.parse import urlparse

import requests

# --------------------------------------------------------------------------
# Reglages
# --------------------------------------------------------------------------

DELAI_ENTRE_REQUETES = 1.0        # secondes, par politesse pour les sites
TIMEOUT = 30
MAX_FICHES_PAR_PASSAGE = 200      # plafond de securite
BUDGET_SECONDES = 20 * 60         # le vrai garde-fou : on s'arrete au temps
AGE_MAX_JOURS = 30                # une annonce plus vieille est ignoree
HEURE_PASSAGE = 8                 # heure de Paris du passage quotidien

DOSSIER = os.path.dirname(os.path.abspath(__file__))
FICHIER_ETAT = os.path.join(DOSSIER, "etat.json")
FICHIER_OFFRES = os.path.join(DOSSIER, "offres.json")
FICHIER_LOG = os.path.join(DOSSIER, "veille.log")
FICHIER_CONFIG = os.path.join(DOSSIER, "config.ini")

ENTETES = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9",
}

# --------------------------------------------------------------------------
# Employeurs suivis. Cle = nom du groupe, valeurs = noms acceptes dans la
# fiche. Les noms de moins de six caracteres sont compares mot a mot, pour
# eviter que "rte" attrape "porte".
# --------------------------------------------------------------------------

EMPLOYEURS = {
    "SPIE":        ["spie", "spie industrie", "spie tertiaire", "spie thepault",
                    "spie facilities", "spie building solutions", "spie citynetworks",
                    "spie nucleaire", "spie ouest centre"],
    "VINCI":       ["vinci", "vinci energies", "vinci construction", "omexom",
                    "citeos", "sogea", "sdel", "cegelec", "eurovia", "axians",
                    "actemium", "botte fondations", "gtie", "gtm ouest",
                    "europeenne de travaux ferroviaires"],
    "EDF":         ["edf", "enedis", "dalkia", "edf renouvelables", "framatome",
                    "jeumont electric", "citelum"],
    "Engie":       ["engie", "engie solutions", "engie green", "endel", "storengy",
                    "cofely"],
    "Eiffage":     ["eiffage", "clemessy", "eiffage energie systemes", "eiffage route"],
    "Bouygues":    ["bouygues", "equans", "colas", "aximum", "bouygues construction",
                    "bouygues batiment", "axima", "ineo"],
    "Airbus":      ["airbus", "airbus atlantic", "testia", "stelia"],
    "SNCF":        ["sncf", "keolis", "geodis", "sncf reseau", "sncf voyageurs"],
    "GRDF":        ["grdf"],
    "NaTran":      ["natran", "grtgaz"],
    "RTE":         ["rte"],
    "Naval Group": ["naval group"],
    "Veolia":      ["veolia"],
    "Suez":        ["suez"],
}

# Ceux-la portent un nom proche mais ne font pas partie des groupes suivis.
EMPLOYEURS_KO = [
    "spie batignolles", "sup de vinci", "ecofac", "ihecf", "formaposte", "afpa",
    "adecco", "manpower", "randstad", "proman", "synergie", "daher", "temporis",
    "portzamparc", "bnp paribas", "actual", "start people", "supplay", "crit",
    "iscod", "studi", "walt", "openclassrooms", "cesi", "cci formation",
]

# --------------------------------------------------------------------------
# Lieu : Nantes et sa proche peripherie uniquement
# --------------------------------------------------------------------------

COMMUNES_OK = [
    "nantes", "saint-herblain", "saint herblain", "reze", "orvault", "carquefou",
    "bouguenais", "vertou", "coueron", "saint-sebastien-sur-loire",
    "saint sebastien sur loire", "la chapelle-sur-erdre", "la chapelle sur erdre",
    "sainte-luce-sur-loire", "sainte luce sur loire", "basse-goulaine",
    "basse goulaine", "thouare-sur-loire", "thouare sur loire", "sautron",
    "treillieres", "bouaye", "saint-aignan-grandlieu", "saint aignan de grand lieu",
    "le pellerin", "indre", "indret", "saint-etienne-de-montluc",
    "saint etienne de montluc", "heric", "la montagne", "saint-jean-de-boiseau",
    "les sorinieres", "sainte-luce", "carquefou cedex", "nantes cedex",
]

# Ecartees meme si elles sont en Loire-Atlantique : trop loin.
COMMUNES_KO = [
    "saint-nazaire", "saint nazaire", "montoir", "donges", "la baule", "pornic",
    "ancenis", "chateaubriant", "guerande", "savenay", "pontchateau", "clisson",
    "blain", "nort-sur-erdre", "machecoul", "saint-brevin", "paimboeuf",
]

# --------------------------------------------------------------------------
# Contrat, niveau, domaines
# --------------------------------------------------------------------------

MOTS_ALTERNANCE = ["alternance", "alternant", "apprentissage", "apprenti",
                   "contrat pro", "professionnalisation"]

CONTRAT_KO = ["stage de fin d'etudes", "stage conventionne", "convention de stage",
              "pfe", "projet de fin d'etudes", "vie ", "volontariat international",
              "interim", "mission interimaire"]

NIVEAU_OK = ["bac+4", "bac + 4", "bac+5", "bac + 5", "master 1", "master 2",
             "master ii", "master i ", "mastere", "ingenieur", "ecole d'ingenieur",
             "cycle ingenieur", "niveau 7", "m1 ", "m2 ", "diplome d'ingenieur"]

NIVEAU_KO = ["cap ", "bep ", "bac pro", "baccalaureat professionnel", "cqp",
             "cqpm", "bts", "but ", "b.u.t", "dut", "licence pro",
             "licence professionnelle", "bac+2", "bac + 2", "bac+3", "bac + 3",
             "bachelor", "niveau 5", "niveau 6", "titre professionnel", "mention complementaire"]

DOMAINES = {
    "technique": [
        "energie", "electrotechnique", "electricite", "electrique", "reseaux",
        "thermique", "cvc", "genie climatique", "automatisme", "automaticien",
        "instrumentation", "bureau d'etudes", "methodes", "methode", "essais", "embarque",
        "maintenance", "fiabilite",
        "maintenance industrielle", "industrialisation", "mecanique", "hydraulique",
        "courant faible", "courants forts", "htb", "hta", "poste source",
        "controle commande", "supervision", "robotique", "conception",
    ],
    "energie": [
        "efficacite energetique", "performance energetique", "audit energetique",
        "renovation energetique", "gtb", "gtc", "pilotage energetique",
        "reseau de chaleur", "reseaux de chaleur", "photovoltaique", "solaire",
        "eolien", "hydrogene", "stockage d'energie", "raccordement", "decarbonation",
        "bilan carbone", "cee", "transition energetique", "energies renouvelables",
        "enr", "biomasse", "geothermie", "methanisation", "sobriete energetique",
    ],
    "projet": [
        "charge d'affaires", "chargee d'affaires", "ingenieur d'affaires",
        "chef de projet", "conducteur de travaux", "conductrice de travaux",
        "contract manager", "etudes de prix", "chiffrage", "planification",
        "planificateur", "gestion de projet", "maitrise d'oeuvre", "pilotage de projet",
        "responsable d'affaires", "developpement de projets",
    ],
    "qse": [
        "qse", "hse", "qhse", "sse", "hsse", "qualite securite environnement",
        "sante securite", "prevention des risques", "amelioration continue",
        "performance industrielle", "lean", "excellence operationnelle",
        "environnement", "surete", "qualite",
    ],
}

ORDRE_FAMILLES = ("projet", "energie", "qse", "technique")

NOMS_DOMAINES = {
    "technique": "Technique",
    "energie": "Performance energetique et EnR",
    "projet": "Conduite de projet et d'affaires",
    "qse": "QSE et amelioration continue",
}

DOMAINE_KO = [
    "ressources humaines", "rh ", "paie", "recrutement", "achats", "acheteur",
    "logistique", "supply chain", "communication", "marketing", "juridique",
    "comptabilite", "comptable", "controle de gestion", "controleur de gestion",
    "commercial", "vente", "sirh", "administrateur systeme", "developpeur",
    "data analyst", "gestionnaire de donnees", "assistant de gestion",
    "secretaire", "assistanat", "finance", "audit interne", "formation",
    "assistant", "assistante", "gestionnaire d'actifs", "gestion d'actifs",
    "chargee de clientele", "charge de clientele", "relation client", "back office",
]

METIERS_KO = [
    "coffreur", "macon", "menuisier", "soudeur", "tuyauteur", "chaudronnier",
    "monteur", "cableur", "terrassier", "poseur", "ouvrier", "operateur",
    "agent d'exploitation", "aide chef d'equipe", "conducteur d'engins",
    "peintre", "ajusteur", "outilleur", "bobinier", "mecanicien",
    "electricien", "electromecanicien", "technicien de maintenance",
    "negociateur", "conducteur de train", "conducteur de tram", "agent de maintenance",
    "plombier", "serrurier", "canalisateur", "manoeuvre", "magasinier",
    "technicien", "technicienne", "installateur", "installatrice", "frigoriste",
    "agent technique", "agent de proprete", "preparateur", "monteuse",
]

# --------------------------------------------------------------------------
# Sources. Pages de liste par employeur, deja filtrees sur l'alternance et le
# departement. La reference capturee par le motif sert d'identifiant.
# --------------------------------------------------------------------------

# Pages Jobijoba a interroger, groupe par groupe. La page d'un groupe ne
# remonte PAS toujours les annonces de ses filiales : en octobre 2026, la page
# EDF ne montrait aucune des cinq annonces Enedis. Chaque filiale qui publie
# sous son propre nom a donc sa propre page. Le slug est le nom tel que
# Jobijoba l'attend dans l'URL, espaces remplaces par des +.
# Ajouter une filiale ici est sans risque : si Jobijoba ne connait pas le nom,
# la page est detectee comme generique et ignoree (voir page_generique).
SLUGS = {
    "SPIE":        ["SPIE", "SPIE+Thepault", "SPIE+Industrie", "SPIE+Facilities",
                    "SPIE+Citynetworks", "SPIE+Building+Solutions"],
    "VINCI":       ["VINCI", "VINCI+Energies", "VINCI+Construction", "Omexom", "Citeos",
                    "Cegelec", "Actemium", "Axians", "Sogea", "SDEL", "Eurovia",
                    "Botte+Fondations", "GTM+Ouest"],
    "EDF":         ["EDF", "Enedis", "Dalkia", "EDF+Renouvelables", "Framatome"],
    "Engie":       ["ENGIE", "Engie+Solutions", "Engie+Green", "Endel", "Storengy"],
    "Eiffage":     ["Eiffage", "Eiffage+Energie+Systemes", "Clemessy"],
    # Equans n'a pas de page propre sur Jobijoba (nom inconnu), mais la page
    # Axima remonte toutes ses annonces : 15 en octobre 2026, contre 4 sur la
    # page Bouygues. C'est de loin la page filiale la plus utile.
    "Bouygues":    ["Bouygues", "Bouygues+Construction", "Axima", "Equans", "Ineo",
                    "Colas", "Aximum"],
    "Airbus":      ["Airbus+Group", "Airbus", "Airbus+Atlantic"],
    "SNCF":        ["SNCF", "SNCF+Reseau", "SNCF+Voyageurs", "Keolis"],
    "GRDF":        ["GRDF"],
    "NaTran":      ["Grtgaz", "NaTran"],
    "RTE":         ["RTE"],
    "Naval Group": ["Naval+Group"],
    "Veolia":      ["Veolia"],
    "Suez":        ["Suez"],
}

def sources_jobijoba():
    sources = []
    for groupe, slugs in SLUGS.items():
        for n, slug in enumerate(slugs):
            # le departement pour tout le monde, la ville en plus pour la page
            # principale du groupe, qui ne renvoie pas exactement le meme lot
            zones = ("Loire-atlantique", "Nantes") if n == 0 else ("Loire-atlantique",)
            for zone in zones:
                sources.append({
                    "nom": "JOBIJOBA_" + groupe.upper().replace(" ", ""),
                    "site": "jobijoba",
                    "groupe": groupe,
                    "slug": slug,
                    "url": "https://www.jobijoba.com/fr/alternance/%s/%s" % (slug, zone),
                    "motif": r'/fr/annonce/(\d+/[0-9a-f]{32})',
                    "fiche": "https://www.jobijoba.com/fr/annonce/%s",
                })
    return sources


def page_generique(html, slug):
    """Quand Jobijoba ne connait pas un nom d'entreprise, il ne renvoie pas une
    page vide : il renvoie TOUTES les alternances du departement (1376 en
    octobre 2026), sous le titre 'Alternance en Loire-Atlantique'. Les lire
    viderait le budget de temps sur des offres de vendeur et de commercial.
    On reconnait le cas au titre H1, qui ne contient alors pas le nom cherche."""
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S | re.I)
    if not m:
        return False
    titre = sans_accents(re.sub(r"<[^>]+>", " ", m.group(1)))
    nom = sans_accents(slug.replace("+", " "))
    mots = [w for w in re.split(r"[^a-z0-9]+", nom) if len(w) >= 3]
    return bool(mots) and not any(w in titre for w in mots)

# Second site : HelloWork. Il couvre des employeurs que Jobijoba ne connait pas
# ou relaie mal. En octobre 2026, sa page Equans a Nantes comptait 47 offres
# contre 15 sur Jobijoba, et sa page « alternance master Nantes » remontait une
# offre Veolia d'ingenieur methodes absente de Jobijoba.
# Son robots.txt interdit toute URL avec un « ? », donc pas de pagination :
# on ne lit que la premiere page de chaque liste, triee de la plus recente a
# la plus ancienne. Avec un passage par jour, c'est ce qu'il faut.
# Une adresse qui n'existe pas renvoie une erreur 404, simplement journalisee.
HELLOWORK = [
    # (groupe pour le bilan, chemin apres /fr-fr/)
    # listes thematiques, tous employeurs : le filtre employeur trie ensuite
    ("HelloWork", "alternance/mot-cle_master-ville_nantes-44000.html"),
    ("HelloWork", "alternance/ville_nantes-44000.html"),
    ("HelloWork", "alternance/ville_saint-herblain-44800.html"),
    ("HelloWork", "alternance/ville_carquefou-44470.html"),
    ("HelloWork", "alternance/ville_reze-44400.html"),
    ("HelloWork", "alternance/ville_bouguenais-44340.html"),
    ("HelloWork", "alternance/ville_orvault-44700.html"),
    # pages entreprise a Nantes, tous contrats confondus : le filtre contrat trie
    ("Bouygues", "entreprises/equans-1338/ville_nantes-44000.html"),
    ("Engie",    "entreprises/engie-cofely-8032/ville_nantes-44000.html"),
    ("VINCI",    "entreprises/actemium-loire-ocean-117258.html"),
    ("Veolia",   "entreprises/veolia-103310/ville_nantes-44000.html"),
    ("EDF",      "entreprises/edf-5489/ville_nantes-44000.html"),
    ("SPIE",     "entreprises/spie-industrie-et-tertiaire-division-industrie-75834/ville_nantes-44000.html"),
    ("RTE",      "entreprises/rte-7029/ville_nantes-44000.html"),
    ("NaTran",   "entreprises/natran-33461/ville_nantes-44000.html"),
]

def sources_hellowork():
    return [{
        "nom": "HELLOWORK",
        "site": "hellowork",
        "groupe": groupe,
        "slug": None,
        "url": "https://www.hellowork.com/fr-fr/" + chemin,
        "motif": r'/fr-fr/emplois/(\d{6,9})\.html',
        "fiche": "https://www.hellowork.com/fr-fr/emplois/%s.html",
    } for groupe, chemin in HELLOWORK]

# Jobijoba d'abord : ses fiches passent en premier si le temps vient a manquer.
SOURCES = sources_jobijoba() + sources_hellowork()

# --------------------------------------------------------------------------
# Petits outils
# --------------------------------------------------------------------------

_journal = []

def log(message):
    ligne = "%s  %s" % (datetime.now().strftime("%d/%m %H:%M:%S"), message)
    print(ligne, flush=True)
    _journal.append(ligne)

def sans_accents(texte):
    texte = unicodedata.normalize("NFD", texte or "")
    texte = "".join(c for c in texte if unicodedata.category(c) != "Mn")
    return texte.lower()

def contient_mot(texte, mots):
    """Cherche chaque mot dans le texte. Les mots courts sont compares avec
    des frontieres de mot, pour que 'rte' n'attrape pas 'porte'."""
    t = sans_accents(texte)
    for m in mots:
        m = sans_accents(m)
        if len(m.strip()) <= 5:
            if re.search(r"(?<![a-z0-9])" + re.escape(m.strip()) + r"(?![a-z0-9])", t):
                return m
        elif m in t:
            return m
    return None

class Chrono:
    def __init__(self, budget):
        self.debut = time.time()
        self.budget = budget
    def depasse(self):
        return (time.time() - self.debut) > self.budget
    def reste(self):
        return max(0, int(self.budget - (time.time() - self.debut)))

# --------------------------------------------------------------------------
# Reseau, avec respect de robots.txt
# --------------------------------------------------------------------------

_robots = {}

def autorise(url):
    try:
        p = urlparse(url)
        racine = "%s://%s" % (p.scheme, p.netloc)
        if racine not in _robots:
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(racine + "/robots.txt")
            try:
                rp.read()
            except Exception:
                rp = None
            _robots[racine] = rp
        rp = _robots[racine]
        if rp is None:
            return True
        return rp.can_fetch(ENTETES["User-Agent"], url)
    except Exception:
        return True

def telecharger(url):
    if not autorise(url):
        log("  robots.txt interdit : %s" % url)
        return None
    try:
        r = requests.get(url, headers=ENTETES, timeout=TIMEOUT)
        time.sleep(DELAI_ENTRE_REQUETES)
        if r.status_code == 200:
            return r.text
        log("  code %s : %s" % (r.status_code, url))
        return None
    except Exception as e:
        log("  echec : %s (%s)" % (url, e))
        return None

# --------------------------------------------------------------------------
# Lecture d'une fiche : bloc JobPosting
# --------------------------------------------------------------------------

def _textes_jsonld(html):
    blocs = []
    for m in re.finditer(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>',
                         html, re.S | re.I):
        brut = m.group(1).strip()
        try:
            blocs.append(json.loads(brut))
        except Exception:
            try:
                blocs.append(json.loads(re.sub(r",\s*([}\]])", r"\1", brut)))
            except Exception:
                pass
    return blocs

def _aplatir(obj, sortie):
    if isinstance(obj, dict):
        if obj.get("@type") in ("JobPosting", ["JobPosting"]):
            sortie.append(obj)
        for v in obj.values():
            _aplatir(v, sortie)
    elif isinstance(obj, list):
        for v in obj:
            _aplatir(v, sortie)

def _texte_html(html):
    t = re.sub(r"<script.*?</script>", " ", html, flags=re.S | re.I)
    t = re.sub(r"<style.*?</style>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"&nbsp;?", " ", t)
    t = re.sub(r"&[a-z]+;", " ", t)
    return re.sub(r"\s+", " ", t)

MOIS = {"janvier":1,"fevrier":2,"mars":3,"avril":4,"mai":5,"juin":6,"juillet":7,
        "aout":8,"septembre":9,"octobre":10,"novembre":11,"decembre":12}

def date_dans_texte(texte):
    """Beaucoup de fiches n'ont pas de bloc JobPosting et affichent leur date
    en clair : 'Publiee le 11/11/2024', '11 novembre 2024', 'il y a 3 jours'.
    Sans cette lecture, une annonce de 2024 passait pour une annonce du jour."""
    t = sans_accents(texte)[:6000]

    m = re.search(r"il y a (\d{1,3}) jour", t)
    if m:
        d = datetime.now(timezone.utc) - timedelta(days=int(m.group(1)))
        return d.strftime("%Y-%m-%d")
    if "aujourd" in t[:2000] or "il y a quelques heures" in t[:2000]:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", t)
    if m:
        return m.group(0)
    m = re.search(r"(\d{1,2})[/.](\d{1,2})[/.](20\d{2})", t)
    if m:
        return "%s-%02d-%02d" % (m.group(3), int(m.group(2)), int(m.group(1)))
    m = re.search(r"(\d{1,2})\s+(" + "|".join(MOIS) + r")\s+(20\d{2})", t)
    if m:
        return "%s-%02d-%02d" % (m.group(3), MOIS[m.group(2)], int(m.group(1)))
    return ""


def nettoyer_titre(brut):
    """Un titre de repli vient de la balise title de la page et traine tout le
    habillage du site : ' | engie - Nantes - Offre d'emploi Septembre 2026 -
    Jobijoba'. On coupe au premier separateur et on decode les entites."""
    t = _html.unescape(re.sub(r"<[^>]+>", "", brut or ""))
    t = re.sub(r"\s+", " ", t).strip()
    for sep in (" | ", " - Offre d", " - Emploi ", " details du poste", " | Jobijoba"):
        i = sans_accents(t).find(sans_accents(sep))
        if i > 10:
            t = t[:i]
    return t.strip(" -|")


def analyser_fiche(html, url):
    """Renvoie un dictionnaire decrivant l'annonce."""
    fiche = {"url": url, "titre": "", "titre_brut": "", "employeur": "", "employeur_declare": "",
             "commune": "", "date": "", "contrat": "", "description": "",
             "texte": _texte_html(html)[:12000]}

    postings = []
    for bloc in _textes_jsonld(html):
        _aplatir(bloc, postings)

    if postings:
        p = postings[0]
        fiche["titre"] = (p.get("title") or "").strip()
        org = p.get("hiringOrganization") or {}
        if isinstance(org, dict):
            fiche["employeur_declare"] = (org.get("name") or "").strip()
        elif isinstance(org, str):
            fiche["employeur_declare"] = org.strip()
        lieu = p.get("jobLocation")
        if isinstance(lieu, list) and lieu:
            lieu = lieu[0]
        if isinstance(lieu, dict):
            adr = lieu.get("address") or {}
            if isinstance(adr, dict):
                fiche["commune"] = " ".join(str(adr.get(k, "")) for k in
                                            ("addressLocality", "postalCode", "addressRegion"))
        fiche["date"] = (p.get("datePosted") or "")[:10]
        emp = p.get("employmentType")
        if isinstance(emp, list):
            emp = " ".join(str(x) for x in emp)
        fiche["contrat"] = str(emp or "")
        desc = p.get("description") or ""
        fiche["description"] = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", desc))[:6000]

    if not fiche["titre"]:
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
        if m:
            fiche["titre_brut"] = _html.unescape(re.sub(r"<[^>]+>", "", m.group(1)))
            fiche["titre"] = nettoyer_titre(m.group(1))
    else:
        fiche["titre"] = nettoyer_titre(fiche["titre"])
    if not fiche["date"]:
        m = re.search(r'"datePosted"\s*:\s*"(\d{4}-\d{2}-\d{2})', html)
        if m:
            fiche["date"] = m.group(1)
    if not fiche["date"]:
        # la date affichee en clair sur la page, en dernier recours
        fiche["date"] = date_dans_texte(fiche["description"] + " " + fiche["texte"])

    fiche["employeur"] = fiche["employeur_declare"] or ""
    return fiche

# --------------------------------------------------------------------------
# Filtres. Chaque fonction renvoie None si l'offre passe, sinon le motif de
# rejet, en clair, pour le journal.
# --------------------------------------------------------------------------

def _age_jours(date_iso):
    try:
        d = datetime.strptime(date_iso, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - d).days
    except Exception:
        return None

def trouver_groupe(fiche):
    """Cherche l'employeur dans le champ declare et le titre, jamais dans le
    bas de page : c'est ce qui evitait de prendre Portzamparc pour la SNCF."""
    base = (fiche["employeur_declare"] + " " + fiche["titre"])
    if not fiche["employeur_declare"]:
        base += " " + fiche.get("titre_brut", "") + " " + fiche["description"][:1500]
        base += " " + fiche.get("texte", "")[:800]
    if contient_mot(base, EMPLOYEURS_KO):
        return None
    for groupe, noms in EMPLOYEURS.items():
        if contient_mot(base, noms):
            return groupe
    return None

def verifier(fiche):
    """Renvoie (groupe, famille) si l'offre est retenue, sinon (None, motif)."""
    titre = fiche["titre"]
    tout = " ".join([fiche["employeur_declare"], titre, fiche.get("titre_brut", ""),
                     fiche["contrat"], fiche["description"]])

    groupe = trouver_groupe(fiche)
    if not groupe:
        return None, "employeur hors perimetre (%s)" % (fiche["employeur_declare"] or "inconnu")

    struct = sans_accents(fiche["contrat"])
    if "intern" in struct and "apprentice" not in struct:
        pass  # certains sites classent l'alternance en INTERN, on ne tranche pas la
    if not contient_mot(tout, MOTS_ALTERNANCE):
        return None, "contrat non alternance"
    faux = contient_mot(titre, CONTRAT_KO)
    if faux:
        return None, "contrat ecarte (%s)" % faux

    lieu = fiche["commune"] or ""
    hors = contient_mot(lieu, COMMUNES_KO) or contient_mot(titre, COMMUNES_KO)
    if hors:
        return None, "commune trop loin (%s)" % hors
    ici = contient_mot(lieu, COMMUNES_OK) or contient_mot(titre, COMMUNES_OK)
    if not ici:
        ici = contient_mot(fiche["description"][:1500], COMMUNES_OK)
    if not ici:
        ici = contient_mot(fiche.get("texte", "")[:3000], COMMUNES_OK)
    if not ici:
        return None, "commune hors Nantes (%s)" % (lieu.strip() or "non precisee")

    age = _age_jours(fiche["date"])
    if age is None:
        # aucune date lisible : c'est exactement ainsi qu'une annonce Engie de
        # 2024 s'etait glissee dans le suivi. Dans le doute, on ecarte.
        return None, "date introuvable"
    if age > AGE_MAX_JOURS:
        return None, "annonce de plus de %d jours (%s)" % (AGE_MAX_JOURS, fiche["date"])
    if age < -2:
        return None, "date incoherente (%s)" % fiche["date"]

    metier = contient_mot(titre, METIERS_KO)
    if metier:
        # conducteur de travaux est un poste d'ingenieur, il doit passer
        if "conducteur de travaux" not in sans_accents(titre):
            return None, "metier d'execution (%s)" % metier

    # Niveau : un refus dans le titre est sans appel, sinon on lit la fiche.
    mauvais_titre = contient_mot(titre, NIVEAU_KO)
    if mauvais_titre:
        return None, "niveau %s dans l'intitule" % mauvais_titre
    texte_niveau = titre + " " + fiche["description"]
    bon = contient_mot(texte_niveau, NIVEAU_OK)
    mauvais = contient_mot(texte_niveau, NIVEAU_KO)
    if mauvais and not bon:
        return None, "niveau %s" % mauvais

    support = contient_mot(titre, DOMAINE_KO)
    if support:
        return None, "fonction support (%s)" % support

    # Ordre volontaire : un intitule de conduite d'affaires prime sur la
    # technique, sinon "ingenieur d'affaires HTB" serait classe en technique.
    famille = None
    for cle in ORDRE_FAMILLES:
        if contient_mot(titre, DOMAINES[cle]):
            famille = cle
            break
    if not famille:
        for cle in ORDRE_FAMILLES:
            if contient_mot(fiche["description"][:3000], DOMAINES[cle]):
                famille = cle
                break
    if not famille:
        return None, "domaine hors cible"

    fiche["niveau"] = "non precise" if not bon else bon
    return groupe, famille

# --------------------------------------------------------------------------
# Etat et fichier d'offres
# --------------------------------------------------------------------------

def charger_etat():
    if os.path.exists(FICHIER_ETAT):
        try:
            with open(FICHIER_ETAT, encoding="utf-8") as f:
                e = json.load(f)
            e.setdefault("vues", {})
            e.setdefault("dernier_mail", "")
            return e
        except Exception:
            pass
    return {"vues": {}, "dernier_mail": ""}

def ecrire_etat(etat):
    etat["dernier_passage"] = datetime.now(PARIS).strftime("%Y-%m-%d")
    limite = (datetime.now(timezone.utc) - timedelta(days=60)).strftime("%Y-%m-%d")
    etat["signatures"] = {k: v for k, v in etat.get("signatures", {}).items() if v >= limite}
    # on garde les 1500 references les plus recentes
    vues = etat["vues"]
    if len(vues) > 1500:
        gardees = sorted(vues.items(), key=lambda kv: kv[1].get("le", ""), reverse=True)[:1500]
        etat["vues"] = dict(gardees)
    with open(FICHIER_ETAT, "w", encoding="utf-8") as f:
        json.dump(etat, f, ensure_ascii=False, indent=1, sort_keys=True)

def charger_offres():
    if os.path.exists(FICHIER_OFFRES):
        try:
            with open(FICHIER_OFFRES, encoding="utf-8") as f:
                d = json.load(f)
            if isinstance(d, dict) and isinstance(d.get("offres"), list):
                return d
        except Exception:
            pass
    return {"maj": "", "offres": []}

def ecrire_offres(donnees, nouvelles):
    """Ajoute les nouvelles offres sans jamais toucher aux anciennes : la page
    de suivi se sert de ce fichier, et l'identifiant fait foi."""
    connus = {o.get("id") for o in donnees["offres"]}
    for o in nouvelles:
        if o["id"] not in connus:
            donnees["offres"].append(o)
    donnees["offres"] = donnees["offres"][-400:]
    donnees["maj"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    with open(FICHIER_OFFRES, "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=1)

def signature(fiche, groupe):
    """Empreinte d'une offre, pour reperer la meme annonce arrivee deux fois."""
    t = sans_accents(fiche["titre"])
    t = re.sub(r"\b(h/?f|f/?h|alternance|alternant|apprenti|apprentissage)\b", " ", t)
    t = re.sub(r"[^a-z0-9]+", " ", t).strip()
    return (groupe + "|" + t[:40]).strip()

# --------------------------------------------------------------------------
# Mail
# --------------------------------------------------------------------------

def charger_config():
    cfg = {
        "expediteur": os.environ.get("MAIL_EXPEDITEUR", ""),
        "destinataire": os.environ.get("MAIL_DESTINATAIRE", ""),
        "mot_de_passe": os.environ.get("MAIL_MOT_DE_PASSE", ""),
        "serveur": os.environ.get("MAIL_SERVEUR", "smtp.gmail.com"),
        "port": int(os.environ.get("MAIL_PORT", "465")),
        "suivi": os.environ.get("URL_SUIVI", ""),
    }
    if not cfg["expediteur"] and os.path.exists(FICHIER_CONFIG):
        p = configparser.ConfigParser()
        p.read(FICHIER_CONFIG, encoding="utf-8")
        if p.has_section("mail"):
            cfg["expediteur"] = p.get("mail", "expediteur", fallback="")
            cfg["destinataire"] = p.get("mail", "destinataire", fallback="")
            cfg["mot_de_passe"] = p.get("mail", "mot_de_passe", fallback="")
            cfg["serveur"] = p.get("mail", "serveur", fallback="smtp.gmail.com")
            cfg["port"] = p.getint("mail", "port", fallback=465)
        if p.has_section("suivi"):
            cfg["suivi"] = p.get("suivi", "url", fallback="")
    return cfg

def rediger(retenues, stats, url_suivi):
    par_famille = {}
    for o in retenues:
        par_famille.setdefault(o["famille"], []).append(o)

    lignes = []
    html = []
    for cle in ("technique", "energie", "projet", "qse"):
        if cle not in par_famille:
            continue
        lignes.append("")
        lignes.append(NOMS_DOMAINES[cle].upper())
        html.append("<h3>%s</h3><ul>" % NOMS_DOMAINES[cle])
        for o in par_famille[cle]:
            lignes.append("")
            lignes.append("* %s" % o["titre"])
            lignes.append("  %s, %s" % (o["employeur"], o["commune"]))
            lignes.append("  publiee le %s, niveau %s" % (o["publiee"] or "date inconnue", o["niveau"]))
            if o["missions"]:
                lignes.append("  %s" % o["missions"])
            lignes.append("  %s" % o["lien"])
            html.append(
                "<li><b>%s</b><br>%s, %s<br>publiee le %s, niveau %s<br>%s<br>"
                "<a href=\"%s\">Voir l'annonce</a></li>" %
                (o["titre"], o["employeur"], o["commune"], o["publiee"] or "date inconnue",
                 o["niveau"], o["missions"], o["lien"]))
        html.append("</ul>")

    if url_suivi:
        lignes.append("")
        lignes.append("Suivi des candidatures : %s" % url_suivi)
        html.append("<p>Suivi des candidatures : <a href=\"%s\">%s</a></p>" % (url_suivi, url_suivi))

    lignes.append("")
    lignes.append("COLLECTE")
    html.append("<h3>Collecte</h3><ul>")
    for groupe in sorted(stats["par_groupe"]):
        s = stats["par_groupe"][groupe]
        lignes.append("%s : %d vues, %d examinees, %d retenues" % (groupe, s["vues"], s["ouvertes"], s["retenues"]))
        html.append("<li>%s : %d vues, %d examinees, %d retenues</li>" %
                    (groupe, s["vues"], s["ouvertes"], s["retenues"]))
    html.append("</ul>")
    lignes.append("")
    lignes.append("Total : %d annonces vues, %d fiches ouvertes, %d retenues, %d reportees." %
                  (stats["vues"], stats["ouvertes"], len(retenues), stats["reportees"]))
    html.append("<p>Total : %d annonces vues, %d fiches ouvertes, %d retenues, %d reportees.</p>" %
                (stats["vues"], stats["ouvertes"], len(retenues), stats["reportees"]))

    objet = ("Veille alternance inge Nantes : %d offre%s" %
             (len(retenues), "s" if len(retenues) > 1 else "")) if retenues else \
            "Veille alternance inge Nantes : rien de neuf"
    return objet, "\n".join(lignes).strip(), "".join(html)

def envoyer(cfg, objet, texte, html, test):
    if test:
        log("--- MAIL (mode test, rien n'est envoye) ---")
        log("Objet : " + objet)
        print(texte)
        return True
    if not (cfg["expediteur"] and cfg["destinataire"] and cfg["mot_de_passe"]):
        log("Configuration mail incomplete, aucun envoi.")
        return False
    msg = EmailMessage()
    msg["Subject"] = objet
    msg["From"] = cfg["expediteur"]
    msg["To"] = cfg["destinataire"]
    msg.set_content(texte)
    msg.add_alternative("<html><body>%s</body></html>" % html, subtype="html")
    try:
        with smtplib.SMTP_SSL(cfg["serveur"], cfg["port"], timeout=60) as s:
            s.login(cfg["expediteur"], cfg["mot_de_passe"])
            s.send_message(msg)
        log("Mail envoye a %s" % cfg["destinataire"])
        return True
    except Exception as e:
        log("Envoi impossible : %s" % e)
        return False

# --------------------------------------------------------------------------
# Passage
# --------------------------------------------------------------------------

def extraire_refs(html, motif):
    vues, ordre = set(), []
    for m in re.finditer(motif, html):
        ref = m.group(1)
        if ref not in vues:
            vues.add(ref)
            ordre.append(ref)
    return ordre

def passage(test=False, force_mail=False):
    chrono = Chrono(BUDGET_SECONDES)
    etat = charger_etat()
    cfg = charger_config()
    deja = etat["vues"]
    aujourdhui = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    stats = {"vues": 0, "ouvertes": 0, "reportees": 0, "pages": 0, "par_groupe": {}}
    for g in list(EMPLOYEURS) + ["HelloWork"]:
        stats["par_groupe"][g] = {"vues": 0, "ouvertes": 0, "retenues": 0}

    a_examiner = []   # (groupe, source, ref, url)
    connus = set()
    vues_groupe = {g: set() for g in list(EMPLOYEURS) + ["HelloWork"]}

    log("Lecture des pages de liste")
    for src in SOURCES:
        if chrono.depasse():
            log("Budget atteint pendant la collecte.")
            break
        html = telecharger(src["url"])
        if html is None:
            continue
        if src["slug"] and page_generique(html, src["slug"]):
            log("  %-12s %-26s page inconnue de Jobijoba, ignoree" % (src["groupe"], src["slug"]))
            continue
        stats["pages"] += 1
        refs = extraire_refs(html, src["motif"])
        nouvelles_ici = [r for r in refs if r not in vues_groupe[src["groupe"]]]
        vues_groupe[src["groupe"]].update(refs)
        log("  %-12s %-26s %3d annonces dont %d nouvelles pour le groupe  (%s)"
            % (src["groupe"], src["slug"] or src["site"], len(refs), len(nouvelles_ici),
               src["url"].split("/")[-1]))
        for ref in refs:
            # cle par site et par reference : la meme annonce vue sur la page
            # du groupe et sur celle de la filiale n'est ouverte qu'une fois.
            # L'ancienne cle, par groupe, est encore reconnue pour ne pas
            # rouvrir ce qui a deja ete traite avant ce changement.
            site = src["site"].upper()
            cle = site + "|" + ref
            ancienne = src["nom"] + "|" + ref
            if cle in deja or ancienne in deja or cle in connus:
                continue
            connus.add(cle)
            a_examiner.append((src["groupe"], site, ref, src["fiche"] % ref))

    for g, refs in vues_groupe.items():
        stats["par_groupe"][g]["vues"] = len(refs)
    stats["vues"] = len(set().union(*vues_groupe.values())) if vues_groupe else 0

    log("%d annonces jamais vues" % len(a_examiner))

    retenues, signatures = [], set()
    for i, (groupe, source, ref, url) in enumerate(a_examiner):
        if chrono.depasse() or i >= MAX_FICHES_PAR_PASSAGE:
            stats["reportees"] = len(a_examiner) - i
            log("Arret : %d annonces reportees au prochain passage." % stats["reportees"])
            break
        html = telecharger(url)
        cle = source + "|" + ref
        if html is None:
            continue
        stats["ouvertes"] += 1
        stats["par_groupe"][groupe]["ouvertes"] += 1
        fiche = analyser_fiche(html, url)
        g, famille_ou_motif = verifier(fiche)
        if not g:
            deja[cle] = {"le": aujourdhui, "motif": famille_ou_motif}
            log("  ecartee : %-55s %s" % (fiche["titre"][:55], famille_ou_motif))
            continue
        # la meme offre publiee sur les deux sites : on ne la signale qu'une
        # fois, ni dans ce passage, ni dans les soixante jours qui suivent
        sig = signature(fiche, g)
        if sig in signatures or sig in etat.setdefault("signatures", {}):
            deja[cle] = {"le": aujourdhui, "motif": "doublon d'une offre deja signalee"}
            continue
        signatures.add(sig)
        etat["signatures"][sig] = aujourdhui
        offre = {
            "id": (source.lower() + "-" + ref.split("/")[-1]).lower(),
            "titre": fiche["titre"],
            "employeur": fiche["employeur_declare"] or g,
            "groupe": g,
            "commune": re.sub(r"\s+", " ", fiche["commune"]).strip(),
            "famille": famille_ou_motif,
            "niveau": fiche.get("niveau", "non precise"),
            "publiee": fiche["date"],
            "lien": url,
            "missions": fiche["description"][:280],
            "source": "veille",
            "ajoutee": aujourdhui,
        }
        retenues.append(offre)
        deja[cle] = {"le": aujourdhui, "motif": "retenue"}
        stats["par_groupe"][g]["retenues"] += 1
        log("  RETENUE : %s (%s, %s)" % (offre["titre"], offre["employeur"], offre["commune"]))

    # Mail
    envoyer_mail, motif_silence = bool(retenues), ""
    if not retenues:
        dernier = etat.get("dernier_mail", "")
        vieux = True
        if dernier:
            try:
                jours = (datetime.now(timezone.utc) -
                         datetime.strptime(dernier, "%Y-%m-%d").replace(tzinfo=timezone.utc)).days
                vieux = jours >= 7
                motif_silence = ("rien de neuf, et un mail est deja parti il y a %d jour(s) "
                                 "(regle des sept jours)" % jours)
            except Exception:
                vieux = True
        envoyer_mail = vieux
    if force_mail and not envoyer_mail:
        envoyer_mail, motif_silence = True, ""
        log("Lancement a la main : le mail part meme s'il n'y a rien de neuf.")

    if stats["pages"] == 0:
        # aucune page de liste lue : ce n'est pas "rien de neuf", c'est une panne
        objet = "Veille alternance Nantes : sources injoignables"
        texte = ("Aucune des %d pages de liste n'a pu etre lue lors du passage du %s.\n"
                 "Rien n'a donc ete examine. Le journal veille.log du depot donne le detail.\n"
                 % (len(SOURCES), aujourdhui))
        html_mail = "<p>%s</p>" % texte.replace("\n", "<br>")
        envoyer(cfg, objet, texte, html_mail, test)
        etat["dernier_mail"] = aujourdhui
        if not test:
            ecrire_etat(etat)
        log("Toutes les sources sont injoignables.")
        return []

    objet, texte, html_mail = rediger(retenues, stats, cfg["suivi"])
    if envoyer_mail:
        if envoyer(cfg, objet, texte, html_mail, test):
            etat["dernier_mail"] = aujourdhui
    else:
        log("MAIL NON ENVOYE : %s." % (motif_silence or "rien a signaler"))
        log("Pour recevoir quand meme un mail, relance le workflow a la main : "
            "un lancement manuel force l'envoi.")

    if not test:
        ecrire_etat(etat)
        ecrire_offres(charger_offres(), retenues)
        try:
            with open(FICHIER_LOG, "a", encoding="utf-8") as f:
                f.write("\n".join(_journal) + "\n\n")
        except Exception:
            pass

    log("Termine : %d retenues, %d fiches ouvertes, %d reportees, %ds restantes."
        % (len(retenues), stats["ouvertes"], stats["reportees"], chrono.reste()))
    return retenues

def heure_de_passer(etat, maintenant=None):
    """GitHub ne connait que l'heure UTC, alors que 8h a Paris tombe a 06:00
    UTC l'ete et a 07:00 UTC l'hiver. Le workflow se declenche donc aux deux
    heures, et c'est ici que l'on choisit : on passe si l'heure de Paris a
    atteint HEURE_PASSAGE et qu'aucun passage n'a encore eu lieu aujourd'hui.
    L'ete, 06:00 UTC donne 8h, il passe, et 07:00 UTC voit qu'il est deja passe.
    L'hiver, 06:00 UTC donne 7h, trop tot, et 07:00 UTC donne 8h, il passe.
    Un retard de GitHub ne fait pas sauter de jour."""
    maintenant = (maintenant or datetime.now(timezone.utc)).astimezone(PARIS)
    if maintenant.hour < HEURE_PASSAGE:
        return False, "il n'est que %dh a Paris" % maintenant.hour
    if etat.get("dernier_passage") == maintenant.strftime("%Y-%m-%d"):
        return False, "passage deja fait aujourd'hui"
    return True, ""


def main():
    if "--reset" in sys.argv:
        for f in (FICHIER_ETAT,):
            if os.path.exists(f):
                os.remove(f)
        log("Etat efface.")
        return
    if os.environ.get("GITHUB_EVENT_NAME", "") == "schedule":
        ok, motif = heure_de_passer(charger_etat())
        if not ok:
            log("Pas de passage maintenant : %s." % motif)
            return
    force = ("--force-mail" in sys.argv
             or os.environ.get("GITHUB_EVENT_NAME", "") == "workflow_dispatch")
    passage(test="--test" in sys.argv, force_mail=force)

if __name__ == "__main__":
    main()
