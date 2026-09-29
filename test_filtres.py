# -*- coding: utf-8 -*-
"""Controle des filtres sur des cas reels rencontres depuis septembre."""
import json
import veille

def fiche(titre, employeur, commune, description="", date="2026-09-25", contrat="Alternance"):
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
