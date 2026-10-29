# -*- coding: utf-8 -*-
"""Controle des filtres sur des cas reels rencontres depuis septembre."""
import json
from datetime import datetime, timedelta
import veille

IL_Y_A_3_JOURS = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")

def fiche(titre, employeur, commune, description="", date=None, contrat="Alternance"):
    date = date or IL_Y_A_3_JOURS
    jp = {"@context": "https://schema.org", "@type": "JobPosting", "title": titre,
          "hiringOrganization": {"@type": "Organization", "name": employeur},
          "jobLocation": {"@type": "Place", "address": {"@type": "PostalAddress",
                          "addressLocality": commune, "postalCode": "44000"}},
          "datePosted": date, "employmentType": contrat,
          "description": "<p>" + description + "</p>"}
    html = ("<html><head><title>%s</title>"
            "<script type=\"application/ld+json\">%s</script></head>"
            "<body>%s SNCF Veolia mentions legales</body></html>"
            % (titre, json.dumps(jp, ensure_ascii=False), description))
    return veille.analyser_fiche(html, "https://exemple.test/annonce")

CAS = [
    # (attendu retenu ?, famille attendue, fiche)
    (True,  "projet",    fiche("Alternance Ingenieur d'affaires HTB H/F", "SPIE Thepault", "Saint-Herblain",
                               "Vous preparez un diplome d'ingenieur. Chiffrage et suivi d'affaires postes HTB.")),
    (True,  "qse",       fiche("Alternance Master 2 QSE", "SNCF Reseau", "Nantes",
                               "Master 2 QSE, animation de la politique sante securite.")),
    (True,  "energie",   fiche("Alternant efficacite energetique H/F", "Dalkia", "Orvault",
                               "Ecole d'ingenieur. Audit energetique et pilotage GTB des sites tertiaires.")),
    (True,  "technique", fiche("Alternance ingenieur methodes maintenance", "SPIE Industrie", "Nantes",
                               "Cycle ingenieur, methodes et maintenance industrielle.")),
    (False, None,        fiche("Alternance BTS ATI", "GRDF", "Nantes", "Preparation d'un BTS.")),
    (False, None,        fiche("Alternance chargee de clientele", "BNP Paribas Portzamparc", "Nantes",
                               "Master banque. SNCF n'a rien a voir ici.")),
    (False, None,        fiche("Alternance ingenieur travaux", "Chantiers de l'Atlantique", "Saint-Nazaire",
                               "Ecole d'ingenieur.")),
    (False, None,        fiche("Alternance ingenieur electrique", "Naval Group", "Lorient",
                               "Ecole d'ingenieur.")),
    (True,  "projet",    fiche("Alternance Conducteur de travaux H/F", "Eiffage Energie Systemes", "Reze",
                               "Ecole d'ingenieur ou master, pilotage de chantiers electriques.")),
    (False, None,        fiche("PFE Conducteur de Travaux", "Eiffage Route", "Carquefou",
                               "Stage de fin d'etudes de six mois.")),
    (False, None,        fiche("Alternance electricien d'equipement", "SPIE", "Saint-Herblain",
                               "Preparation d'un CAP electricien.")),
    (False, None,        fiche("Alternance assistant RH", "Engie Solutions", "Nantes",
                               "Master ressources humaines.")),
    (False, None,        fiche("Alternance ingenieur genie civil", "Sup De Vinci", "Nantes",
                               "Ecole d'ingenieur.")),
    (False, None,        fiche("Alternance ingenieur reseaux", "RTE", "Nantes",
                               "Ecole d'ingenieur.", date="2026-06-01")),
    (True,  "technique", fiche("Alternance ingenieur reseaux electriques", "RTE", "Nantes",
                               "Ecole d'ingenieur, etudes de raccordement.")),
    (False, None,        fiche("Alternance monteur cableur", "Enedis", "Carquefou",
                               "Titre professionnel monteur.")),
]

ok = 0
for attendu, famille, f in CAS:
    g, r = veille.verifier(f)
    retenu = g is not None
    juste = (retenu == attendu) and (not attendu or r == famille)
    ok += juste
    print("%-4s %-46s -> %s" % ("OK" if juste else "RATE", f["titre"][:46],
                                ("retenue %s/%s" % (g, r)) if retenu else "ecartee : " + str(r)))
print("\n%d/%d conformes" % (ok, len(CAS)))

# --- cas issus du premier passage reel du 29 septembre ---------------------
print("\nCas du premier passage reel :")
REELS = [
    (False, fiche("Technicien specialise / Technicienne specialisee CVC (H/F)", "SPIE", "Saint-Herblain",
                  "L'installateur chauffage et climatisation installe et entretient les systemes CVC.")),
    (False, fiche("ALTERNANCE - Assistant(e) Gestionnaire d'actifs clients tertiaires", "SNCF", "Nantes",
                  "Gestion des actifs clients tertiaires.")),
    (True,  fiche("Ingenieur d'affaires (H/F)", "SPIE THEPAULT", "Saint-Herblain",
                  "Dans le cadre de notre developpement, ecole d'ingenieur, affaires industrielles.")),
]
for attendu, f in REELS:
    g, r = veille.verifier(f)
    juste = (g is not None) == attendu
    print("%-4s %-52s -> %s" % ("OK" if juste else "RATE", f["titre"][:52],
                                ("retenue %s/%s" % (g, r)) if g else "ecartee : " + str(r)))

# titre de repli pollue : celui remonte par la page Engie sans JSON-LD
brut = ("Alternance : alternant charge de missions sante securite (h/f) details du poste "
        "| engie - Saint-Etienne-de-Montluc - Offre d&#039;emploi Septembre 2026 - Jobijoba")
print("\nTitre nettoye : " + veille.nettoyer_titre(brut))
html_sans_jsonld = "<html><head><title>%s</title></head><body>Saint-Etienne-de-Montluc</body></html>" % brut
f = veille.analyser_fiche(html_sans_jsonld, "https://exemple.test/x")
g, r = veille.verifier(f)
print("Offre Engie sans donnees structurees -> %s" % (("retenue %s/%s" % (g, r)) if g else "ecartee : " + str(r)))

# --- dates lues dans le texte, quand la fiche n'a pas de JobPosting -------
print("\nLecture de la date dans le texte :")
def page(titre, corps):
    return veille.analyser_fiche(
        "<html><head><title>%s</title></head><body>%s</body></html>" % (titre, corps),
        "https://exemple.test/x")

CAS_DATE = [
    ("Engie 2024", False,
     page("Alternance : alternant charge de missions sante securite (h/f) | engie - Saint-Etienne-de-Montluc",
          "Engie Solutions Saint-Etienne-de-Montluc Publiee le 11/11/2024 sante securite alternance ecole d'ingenieur")),
    ("Engie datee d'hier", True,
     page("Alternance : alternant charge de missions sante securite (h/f) | engie - Saint-Etienne-de-Montluc",
          "Engie Solutions Saint-Etienne-de-Montluc il y a 1 jour sante securite alternance ecole d'ingenieur")),
    ("SNCF 11 novembre 2025", False,
     page("Alternance ingenieur energie | SNCF - Nantes",
          "SNCF Nantes publiee le 11 novembre 2025 alternance ecole d'ingenieur energie")),
    ("Sans aucune date", False,
     page("Alternance ingenieur energie | SPIE - Nantes",
          "SPIE Nantes alternance ecole d'ingenieur energie electrotechnique")),
]
for nom, attendu, f in CAS_DATE:
    g, r = veille.verifier(f)
    juste = (g is not None) == attendu
    print("%-4s %-24s date lue %-12s -> %s" % ("OK" if juste else "RATE", nom, f["date"] or "aucune",
          ("retenue %s/%s" % (g, r)) if g else "ecartee : " + str(r)))


# --- pages de liste : reconnaitre une page generique de Jobijoba ------------
print("\nDetection des pages generiques :")
PAGES = [
    ("Actemium inconnu", True,  "<h1>Alternance en Loire-Atlantique</h1>", "Actemium"),
    ("Enedis connu",     False, "<h1>Alternance Enedis en Loire-Atlantique</h1>", "Enedis"),
    ("Airbus Group",     False, "<h1 class='x'>Alternance Airbus Group en Loire-Atlantique</h1>", "Airbus+Group"),
    ("SNCF Reseau",      False, "<h1>Alternance SNCF R&eacute;seau en Loire-Atlantique</h1>", "SNCF+Reseau"),
    ("GTM Ouest inconnu",True,  "<h1>Alternance en Loire-Atlantique</h1>", "GTM+Ouest"),
    ("page sans H1",     False, "<title>x</title>", "Omexom"),
]
for nom, attendu, html, slug in PAGES:
    r = veille.page_generique(html, slug)
    print("%-4s %-18s -> %s" % ("OK" if r == attendu else "RATE", nom, "generique, ignoree" if r else "lue"))


# --- horaire : un seul passage par jour, a 8h de Paris, ete comme hiver -----
print("\nHoraire du passage quotidien :")
from datetime import timezone as _tz
def utc(j, h, m=0):
    return datetime(2026, j[1], j[0], h, m, tzinfo=_tz.utc)
CAS_HEURE = [
    # (nom, instant UTC du declenchement GitHub, dernier passage, doit passer ?)
    ("ete, 06:00 UTC = 8h",           utc((15, 7), 6),      "",           True),
    ("ete, 07:00 UTC, deja passe",    utc((15, 7), 7),      "2026-07-15", False),
    ("ete, 06:00 UTC en retard 07:40",utc((15, 7), 7, 40),  "",           True),
    ("hiver, 06:00 UTC = 7h",         utc((15, 12), 6),     "",           False),
    ("hiver, 07:00 UTC = 8h",         utc((15, 12), 7),     "",           True),
    ("hiver, 07:00 UTC en retard",    utc((15, 12), 7, 55), "",           True),
    ("lendemain d'un passage",        utc((16, 12), 7),     "2026-12-15", True),
]
for nom, instant, dernier, attendu in CAS_HEURE:
    ok, motif = veille.heure_de_passer({"dernier_passage": dernier}, instant)
    print("%-4s %-32s -> %s" % ("OK" if ok == attendu else "RATE", nom, "passe" if ok else "attend : " + motif))


# --- HelloWork : l'offre Veolia trouvee le 29 octobre, absente de Jobijoba ---
print("\nOffres HelloWork :")
CAS_HW = [
    (True, "technique", fiche("Alternant Ingenieur Methode & Support Maintenance - Outils de Pesage H/F",
          "Veolia Recyclage et Valorisation des Dechets", "Nantes", "Formation ingenieur.")),
    (False, None, fiche("Alternance Chef de Projet CRM & Acquisition Digitale - Bac+5 H/F",
          "Cesacom Nantes", "Nantes", "Ecole de commerce.")),
    (False, None, fiche("Alternant Technicien Projet Chiffrage CVC H/F", "Equans France", "Orleans",
          "BTS fluides energies.")),
]
for attendu, famille, f in CAS_HW:
    g, r = veille.verifier(f)
    juste = (g is not None) == attendu and (not attendu or r == famille)
    print("%-4s %-52s -> %s" % ("OK" if juste else "RATE", f["titre"][:52],
          ("retenue %s/%s" % (g, r)) if g else "ecartee : " + str(r)))

# --- passage de test du 29 octobre : faux positifs et doublon --------------
print("\nCas du passage de test du 29 octobre :")
CAS_OCT = [
    (False, fiche("Alternance : Appui a la gestion des contrats d'alternance F/H (2026-184204)",
                  "Enedis", "Nantes", "Master ressources humaines, suivi administratif et qualite.")),
    (False, fiche("Apprenti Ambulancier F/H", "Keolis Sante", "Nantes",
                  "Formation au diplome d'Etat, securite et qualite des transports.")),
    (False, fiche("Alternance ingenieur QSE", "Keolis", "Saint-Philbert-de-Grand-Lieu",
                  "Ecole d'ingenieur, sante securite.")),
]
for attendu, f in CAS_OCT:
    g, r = veille.verifier(f)
    juste = (g is not None) == attendu
    print("%-4s %-52s -> %s" % ("OK" if juste else "RATE", f["titre"][:52],
          ("retenue %s/%s" % (g, r)) if g else "ecartee : " + str(r)))

print("\nEmpreintes de doublons :")
CAS_SIG = [
    (True,  "Alternance : Appui a la gestion des contrats d'alternance F/H (2026-184204)",
            "Appui a la gestion des contrats d'alternance F/H"),
    (True,  "Alternant controleur de gestion h/f - Nantes", "Alternant controleur de gestion H/F"),
    (False, "Alternance Master 1 QSE", "Alternance Master 2 QSE"),
    (False, "Chef de projet - Eolien", "Chef de projet - Solaire"),
]
for attendu, a, b in CAS_SIG:
    pareil = veille.signature({"titre": a}, "EDF") == veille.signature({"titre": b}, "EDF")
    print("%-4s %-40s / %-34s -> %s" % ("OK" if pareil == attendu else "RATE", a[:40], b[:34],
          "meme offre" if pareil else "offres distinctes"))

# --- robots.txt : HelloWork refuse l'agent Python-urllib, pas le notre ----
print("\nLecture de robots.txt :")
import urllib.robotparser
rp = urllib.robotparser.RobotFileParser()
rp.parse(["User-Agent: *", "Disallow: /*?", "Disallow: /fr-fr/candidat/", "",
          "User-Agent: Python-urllib", "User-Agent: Wget", "Disallow: /"])
UA = veille.ENTETES["User-Agent"]
CAS_ROBOTS = [
    (True,  "/fr-fr/alternance/ville_nantes-44000.html"),
    (True,  "/fr-fr/entreprises/equans-1338/ville_nantes-44000.html"),
    (False, "/fr-fr/candidat/compte.html"),
]
for attendu, chemin in CAS_ROBOTS:
    r = rp.can_fetch(UA, "https://www.hellowork.com" + chemin)
    print("%-4s %-56s -> %s" % ("OK" if r == attendu else "RATE", chemin, "autorise" if r else "interdit"))

print("\nTitres HelloWork de repli :")
brut = "Offre Emploi Alternance Ingénieur Travaux Télécom Saint-Herblain (44) - Recrutement par Axians | HelloWork"
t = veille.nettoyer_titre(brut)
print("%-4s %s" % ("OK" if "recrutement" not in veille.sans_accents(t) else "RATE", t))

# --- API : reponses simulees, pour tester la lecture sans cle --------------
print("\nLecture des API (reponses simulees) :")

class Reponse:
    def __init__(self, code, donnees):
        self.status_code, self._d = code, donnees
    def json(self):
        return self._d

HIER = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT08:00:00.000Z")
LBA = {"jobs": [
    {"identifier": {"id": "6721abc", "partner_label": "La bonne alternance", "partner_job_id": "x"},
     "workplace": {"name": "ENEDIS", "brand": None, "legal_name": "ENEDIS",
                   "location": {"address": "12 rue X 44000 Nantes"}},
     "apply": {"url": "https://labonnealternance.apprentissage.beta.gouv.fr/emploi/6721abc"},
     "contract": {"type": ["Apprentissage"]},
     "offer": {"title": "Alternance ingenieur poste source H/F", "publication": {"creation": HIER},
               "description": "<p>Ecole d'ingenieur, etudes de raccordement HTA.</p>"}},
    {"identifier": {"id": None, "partner_label": "Hellowork", "partner_job_id": "84/65"},
     "workplace": {"name": "Boulangerie Dupont", "location": {"address": "Reze"}},
     "apply": {"url": "https://exemple.test/2"}, "contract": {"type": ["Apprentissage"]},
     "offer": {"title": "Apprenti vendeur", "publication": {"creation": HIER}, "description": "CAP"}},
], "recruiters": [], "warnings": []}

FT = {"resultats": [
    {"id": "190XYZK", "intitule": "Alternant(e) chef de projet efficacite energetique",
     "description": "Master 2 energie, audit energetique des sites.",
     "dateCreation": HIER, "lieuTravail": {"libelle": "44 - SAINT HERBLAIN", "codePostal": "44800"},
     "entreprise": {"nom": "DALKIA"}, "natureContrat": "Contrat apprentissage",
     "typeContratLibelle": "Contrat a duree determinee - 24 Mois",
     "origineOffre": {"urlOrigine": "https://candidat.francetravail.fr/offres/recherche/detail/190XYZK"}},
]}

vrai_get, vrai_post, vrai_delai = veille.requests.get, veille.requests.post, veille.DELAI_ENTRE_REQUETES
veille.DELAI_ENTRE_REQUETES = 0
def faux_get(url, **kw):
    if "apprentissage.beta" in url:
        return Reponse(200, LBA)
    nature = kw["params"]["natureContrat"]
    return Reponse(200, FT) if nature == "E2" else Reponse(204, None)
veille.requests.get = faux_get
veille.requests.post = lambda url, **kw: Reponse(200, {"access_token": "jeton"})
try:
    lus = veille.offres_lba("cle") + veille.offres_france_travail("id", "secret")
finally:
    veille.requests.get, veille.requests.post = vrai_get, vrai_post
    veille.DELAI_ENTRE_REQUETES = vrai_delai

CAS_API = [  # (reference attendue, retenue attendue, famille attendue)
    ("6721abc", True, "technique"),
    ("Hellowork:84_65", False, None),
    ("190XYZK", True, "projet"),
]
for (ref_att, attendu, famille), (ref, f) in zip(CAS_API, lus):
    g, r = veille.verifier(f)
    juste = ref == ref_att and (g is not None) == attendu and (not attendu or r == famille)
    print("%-4s %-16s %-48s -> %s" % ("OK" if juste else "RATE", ref, f["titre"][:48],
          ("retenue %s/%s" % (g, r)) if g else "ecartee : " + str(r)))
print("%-4s %d offres lues sur 3 attendues" % ("OK" if len(lus) == 3 else "RATE", len(lus)))

print("\nSecrets colles avec des espaces :")
import os
for brut, attendu in [("abc123\n", "abc123"), ("  abc123 \r\n", "abc123"), ("Bearer abc123", "abc123"), ("", "")]:
    os.environ["SECRET_ESSAI"] = brut
    r = veille.secret("SECRET_ESSAI")
    print("%-4s %-22r -> %r" % ("OK" if r == attendu else "RATE", brut, r))
del os.environ["SECRET_ESSAI"]

print("\nRaisons sociales des groupes :")
for nom, attendu in [("ELECTRICITE DE FRANCE", "EDF"), ("GAZ RESEAU DISTRIBUTION FRANCE", "GRDF"),
                     ("RESEAU DE TRANSPORT D'ELECTRICITE", "RTE"), ("DCNS - BU PROPULSION", "Naval Group"),
                     ("SPIE BATIGNOLLES PAYSAGE", None), ("IDEX ENERGIES", None)]:
    g = veille.trouver_groupe({"employeur_declare": nom, "titre": "Alternance", "description": ""})
    print("%-4s %-36s -> %s" % ("OK" if g == attendu else "RATE", nom, g or "hors perimetre"))

print("\nMail et resume des missions :")
r = veille.resume("mot " * 100)
print("%-4s resume coupe au mot (%d car.) -> ...%s" % ("OK" if len(r) <= 281 and r.endswith("mot…") else "RATE", len(r), r[-12:].encode("ascii", "replace").decode()))
print("%-4s texte court intact" % ("OK" if veille.resume("Audit energetique.") == "Audit energetique." else "RATE"))
o = {"id": "lba-6ac", "titre": "R&D <ingenieur>", "employeur": "EDF", "commune": "Nantes", "publiee": "2026-10-28",
     "niveau": "ingenieur", "missions": "a & b", "lien": "https://x.test/?a=1&b=2", "famille": "technique"}
_, texte, html_mail = veille.rediger([o], {"par_groupe": {}, "vues": 1, "ouvertes": 1, "reportees": 0},
                                     "https://exemple.github.io/veille/")
print("%-4s HTML echappe" % ("OK" if "R&amp;D &lt;ingenieur&gt;" in html_mail and "<ingenieur>" not in html_mail else "RATE"))
print("%-4s lien vers la carte du suivi" % ("OK" if "https://exemple.github.io/veille/#offre-lba-6ac" in texte else "RATE"))
