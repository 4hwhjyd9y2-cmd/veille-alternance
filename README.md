# Veille alternance ingenieur, Nantes

Deux outils qui marchent ensemble, heberges sur ce depot :

1. **une veille** : un script Python que GitHub Actions lance un jour sur deux
   a 06:00 UTC, qui parcourt les offres d'alternance de quatorze grands
   groupes a Nantes, filtre, et envoie un mail ;
2. **un suivi de candidatures** : une page web publiee par GitHub Pages, ou
   les offres retenues arrivent toutes seules et ou l'on gere leurs statuts.

Aucun serveur, aucun abonnement, aucune IA a l'execution. Le tout tourne dans
les 2000 minutes gratuites de GitHub Actions, dont la veille consomme environ
150 par mois.

---

## 1. A quoi ca sert, et pour qui

Marin, 23 ans, eleve ingenieur au Cnam, actuellement en alternance chez SPIE
Industrie Ouest, cherche une alternance pour la suite de son cycle ingenieur.
Tout le parametrage decoule de ses contraintes, et c'est ce qui explique la
severite des filtres.

**Ce qu'il cherche**

| Critere | Valeur |
|---|---|
| Contrat | alternance, apprentissage, professionnalisation |
| Niveau | Bac+4 ou Bac+5 uniquement : cycle ingenieur, master |
| Zone | Nantes et sa proche peripherie |
| Employeurs | quatorze grands groupes, filiales comprises |
| Domaines | technique, performance energetique et EnR, conduite de projet et d'affaires, QSE |

**Ce qu'il ne veut pas**, et qui a motive chaque exclusion : les niveaux BTS,
BUT, licence pro et inferieurs ; les metiers d'execution, meme etiquetes
alternance ; les fonctions support, RH, achats, communication, commercial,
informatique de gestion ; les agences d'interim et les organismes de formation
qui republient les offres des autres ; les communes eloignees de Loire-
Atlantique, Saint-Nazaire et Donges comprises ; les stages deguises en
alternance ; les entreprises plus petites que SPIE, dont les avantages sociaux
seraient en retrait.

**Les quatorze groupes suivis** : EDF, VINCI, NaTran, GRDF, Airbus, SPIE,
Bouygues, Eiffage, Engie, Naval Group, RTE, Veolia, Suez, SNCF. Les filiales
sont declarees nommement dans le code, parce que les annonces sortent presque
toujours au nom de la filiale : Omexom, Citeos, Cegelec et Actemium pour VINCI,
Dalkia, Enedis et EDF Renouvelables pour EDF, Equans et Colas pour Bouygues,
Engie Solutions et Engie Green pour Engie, Clemessy pour Eiffage, et ainsi de
suite.

---

## 2. Architecture

```
GitHub Actions (cron, 1 jour sur 2, 06:00 UTC)
        |
        v
    veille.py
        |-- lit  etat.json       (annonces deja vues, pour ne rien signaler deux fois)
        |-- lit  28 pages de liste Jobijoba (14 groupes x 2 zones)
        |-- lit  chaque fiche jamais vue, et son bloc JSON-LD JobPosting
        |-- filtre : employeur, contrat, lieu, date, metier, niveau, domaine
        |-- ecrit etat.json et offres.json
        |-- envoie le mail (SMTP Gmail, mot de passe d'application)
        v
  commit automatique de etat.json, offres.json et veille.log
        |
        v
GitHub Pages sert index.html
        |
        v
  index.html lit offres.json, fusionne les nouveautes dans le
  stockage du navigateur, et affiche le suivi
```

**Le point de conception le plus important** : le script ne lit pas la mise en
page des sites. Il repere les annonces a la forme de leurs URLs, puis lit dans
chaque fiche le bloc de donnees structurees `JobPosting` au format schema.org,
celui que les sites emploi publient pour Google. Ce bloc donne le titre,
l'employeur, le lieu, la date, le type de contrat et la description. Un site
peut donc refaire tout son design sans rien casser.

**La source** est Jobijoba, parce qu'il propose une page deja filtree
« alternance chez tel employeur dans tel departement », ce qui evite de
parcourir des milliers d'annonces. Deux zones sont interrogees par groupe,
`Loire-atlantique` et `Nantes`, parce qu'elles ne renvoient pas exactement le
meme ensemble. Compter un jour de decalage possible avec le site de
l'employeur.

**La separation des roles entre les deux fichiers de donnees** :
`etat.json` est la memoire du script, `offres.json` est le pont vers la page.
Le script n'ecrase jamais une offre deja presente dans `offres.json`, et la
page n'ecrit jamais dans `offres.json`. Les statuts et les notes vivent
uniquement dans le navigateur.

---

## 3. Les fichiers

| Fichier | Role |
|---|---|
| `veille.py` | tout le scan et l'envoi du mail, environ 860 lignes, une seule dependance : `requests` |
| `.github/workflows/veille.yml` | la planification, les secrets, le commit automatique |
| `index.html` | la page de suivi, autonome, sans dependance a part deux polices Google |
| `offres.json` | les offres retenues, ecrit par le script, lu par la page |
| `etat.json` | les references deja traitees, avec la date et le motif de rejet |
| `veille.log` | le journal cumulatif de tous les passages |
| `test_filtres.py` | vingt-trois cas de test sur les filtres, a lancer en local |
| `config.exemple.ini` | modele de configuration, utile seulement hors GitHub |
| `MISE-A-JOUR.md` | la procedure d'installation depuis une tablette |

---

## 4. Le script en detail

### Reglages en haut de fichier

| Constante | Valeur | Role |
|---|---|---|
| `DELAI_ENTRE_REQUETES` | 1.0 s | politesse envers les sites interroges |
| `TIMEOUT` | 30 s | abandon d'une requete trop lente |
| `MAX_FICHES_PAR_PASSAGE` | 120 | plafond de securite |
| `BUDGET_SECONDES` | 20 min | le vrai garde-fou : le passage s'arrete au temps, pas au nombre |
| `AGE_MAX_JOURS` | 30 | au-dela, l'annonce est consideree comme perimee |

### Listes de filtrage

| Liste | Contenu |
|---|---|
| `EMPLOYEURS` | dictionnaire groupe vers noms acceptes, filiales comprises |
| `EMPLOYEURS_KO` | interim, organismes de formation, homonymes (Spie Batignolles, Sup De Vinci) |
| `COMMUNES_OK` | Nantes et sa proche peripherie, une vingtaine de communes |
| `COMMUNES_KO` | Loire-Atlantique mais trop loin : Saint-Nazaire, Montoir, Donges, Ancenis… |
| `MOTS_ALTERNANCE` | ce qui prouve le contrat |
| `CONTRAT_KO` | stage, PFE, VIE, interim |
| `NIVEAU_OK` / `NIVEAU_KO` | Bac+4 et Bac+5 contre tout le reste |
| `DOMAINES` | quatre familles de mots-cles, cles `technique`, `energie`, `projet`, `qse` |
| `ORDRE_FAMILLES` | ordre d'essai des familles, volontairement `projet` avant `technique` |
| `DOMAINE_KO` | fonctions support |
| `METIERS_KO` | metiers d'execution reperables au titre |

### Fonctions principales

- `sources_jobijoba()` construit les 28 pages de liste a interroger.
- `telecharger(url)` respecte `robots.txt` avant chaque requete, via
  `urllib.robotparser`, et attend une seconde apres chaque appel.
- `extraire_refs(html, motif)` sort les references d'annonces d'une page de
  liste, par expression reguliere sur la forme des URLs.
- `analyser_fiche(html, url)` lit le bloc `JobPosting`, et retombe sur la
  balise `title` et le texte brut de la page quand ce bloc manque.
- `nettoyer_titre(brut)` coupe l'habillage du site dans un titre de repli et
  decode les entites HTML.
- `date_dans_texte(texte)` lit une date affichee en clair : `2026-09-24`,
  `11/11/2024`, `11 novembre 2024`, « il y a 3 jours ».
- `contient_mot(texte, mots)` cherche un mot dans un texte, avec frontieres de
  mot pour les mots de cinq caracteres ou moins.
- `trouver_groupe(fiche)` identifie l'employeur.
- `verifier(fiche)` applique tous les filtres et renvoie soit
  `(groupe, famille)`, soit `(None, motif de rejet en clair)`.
- `signature(fiche, groupe)` calcule une empreinte pour fusionner la meme
  annonce arrivee par deux chemins.
- `passage(test, force_mail)` orchestre le tout.

### Ordre des filtres, et pourquoi

L'ordre n'est pas anodin, chaque etape a ete placee apres un vrai faux positif.

1. **Employeur**, juge sur le champ employeur declare et le titre, jamais sur
   le bas de page.
2. **Contrat**, cherche dans le titre, la description et le champ
   `employmentType` des donnees structurees.
3. **Lieu**, la commune de la fiche fait foi, pas celle affichee par
   l'agregateur.
4. **Date**, moins de trente jours, et une annonce sans date lisible est
   ecartee.
5. **Metier**, ecarte les intitules d'execution.
6. **Niveau**, un refus dans le titre est sans appel, sinon le titre et la
   description sont lus ensemble.
7. **Domaine**, quatre familles, essayees d'abord sur le titre puis sur la
   description.

### Envoi du mail

Trois cas :

- **des offres** : mail detaille, regroupe par famille, avec le lien vers la
  page de suivi et un bloc « Collecte » qui donne, groupe par groupe, le nombre
  d'annonces vues, examinees et retenues ;
- **rien de neuf** : mail seulement si le dernier date de plus de sept jours,
  pour ne pas polluer. Le journal ecrit alors pourquoi il se tait ;
- **aucune page lue** : mail « sources injoignables », different de « rien de
  neuf », parce qu'une panne ne doit jamais ressembler a un resultat.

**Un lancement a la main force l'envoi.** Le script detecte
`GITHUB_EVENT_NAME=workflow_dispatch`, ou l'option `--force-mail`.

### Options en ligne de commande

```
python veille.py                passage normal
python veille.py --test         aucun mail envoye, le mail est affiche
python veille.py --force-mail   envoie meme s'il n'y a rien de neuf
python veille.py --reset        oublie toutes les annonces deja vues
python test_filtres.py          rejoue les vingt-trois cas de test
```

---

## 5. La page de suivi

Une seule page, `index.html`, sans framework. Les donnees vivent dans le
`localStorage` du navigateur, sous la cle `suivi-alternance-v1`.

**Statuts** : a etudier, a postuler, postule, relance, entretien, accepte,
refus, archive. Passer une offre a « postule » enregistre la date du jour.
Dix jours plus tard sans changement, un bandeau signale la relance.

**Fusion** : au chargement, la page lit `offres.json` et ajoute les offres dont
l'identifiant est inconnu. Elle ne touche jamais a une offre deja presente,
donc les statuts et les notes survivent a tous les passages de la veille. Les
offres supprimees a la main sont memorisees sous la cle
`suivi-alternance-supprimes` et ne reviennent pas.

**Sauvegarde** : boutons d'export et d'import en JSON. Indispensable, puisque
le stockage navigateur ne survit ni a un effacement des donnees de navigation,
ni a un changement d'appareil.

**Limite connue** : la page doit etre servie par une adresse `https`. Chrome
refuse le stockage local a une page ouverte depuis un fichier telecharge.

---

## 6. Ce qui a deja ete corrige, et pourquoi

Cette section est la plus utile en cas de modification : chaque regle du code
vient d'un vrai faux positif. Les reintroduire serait refaire les memes
erreurs.

| Symptome observe | Cause | Correctif en place |
|---|---|---|
| Une offre BNP Portzamparc classee SNCF | l'employeur etait cherche dans toute la page, or « SNCF » apparait dans le pied de page de l'agregateur | l'employeur n'est juge que sur le champ declare et le titre |
| « RTE » attrapait porte, carte, ouverte | recherche par sous-chaine | `contient_mot` impose des frontieres de mot sous six caracteres |
| « Alternance BTS ATI » retenue | le niveau acceptable etait teste avant le niveau refuse | un refus de niveau dans le titre est sans appel |
| Conducteur de travaux ecarte | le mot « conducteur » figurait parmi les metiers d'execution | exception explicite, conducteur de travaux est un poste d'ingenieur |
| PFE Eiffage annonce a Carquefou, en realite a Tours | lieu lu sur l'agregateur | la fiche fait foi, et « PFE » est un motif de rejet du contrat |
| Une offre SPIE de 2019 remontee | pas de date dans les donnees structurees | lecture de la date dans le texte, et rejet si elle reste introuvable |
| Une offre Engie du 11/11/2024 remontee | date absente, donc filtre des trente jours inapplique | idem, et une date incoherente dans le futur est aussi rejetee |
| La meme offre deux fois dans le suivi | l'identifiant contenait le nom du groupe, donc deux pages donnaient deux identifiants | l'identifiant est `jobijoba-<reference>`, independant du chemin |
| Technicien CVC retenu | la liste ne contenait que « technicien de maintenance » | « technicien » seul, plus installateur et frigoriste |
| Assistant gestionnaire d'actifs SNCF retenu | la liste ne contenait que « assistant de gestion » | « assistant » seul, plus gestionnaire d'actifs |
| Titre illisible avec l'habillage du site | fiche sans donnees structurees, titre pris dans la balise `title` | `nettoyer_titre` coupe au premier separateur et decode les entites |
| « Ingenieur d'affaires HTB » classe en technique | le mot HTB est dans la famille technique | `ORDRE_FAMILLES` place `projet` avant `technique` |
| Lancement manuel sans reponse | la regle des sept jours s'appliquait aussi aux lancements manuels | un lancement manuel force l'envoi |
| Un mail au HTML casse suivi d'un correctif | le HTML etait place dans le corps texte | deux versions distinctes, `set_content` en texte et `add_alternative` en HTML |

---

## 7. Modifier les criteres

Tout est en clair en haut de `veille.py`. Depuis un navigateur : ouvrir le
fichier dans le depot, icone crayon, modifier, **Commit changes**.

| Objectif | Ou toucher |
|---|---|
| Elargir a Bac+3 | retirer `bac+3`, `licence pro`, `bachelor` de `NIVEAU_KO` |
| Accepter Saint-Nazaire | deplacer les communes de `COMMUNES_KO` vers `COMMUNES_OK` |
| Ajouter un employeur | une entree dans `EMPLOYEURS` et une ligne dans `sources_jobijoba()` |
| Accepter les stages | ajouter `stage` dans `MOTS_ALTERNANCE` et vider `CONTRAT_KO` |
| Rouvrir les fonctions support | vider `DOMAINE_KO` |
| Remonter des annonces plus anciennes | augmenter `AGE_MAX_JOURS` |
| Accepter les offres sans date | dans `verifier`, retirer le rejet `date introuvable` |
| Changer l'heure ou la frequence | la ligne `cron` de `veille.yml`, en UTC |
| Changer l'adresse du mail | les secrets du depot, pas le code |

**Apres toute modification des filtres, lancer `python test_filtres.py`.** Les
vingt-trois cas rejouent les faux positifs du tableau precedent. Ajouter un cas quand
un nouveau probleme apparait : c'est ce qui evite les regressions.

---

## 8. Reglages GitHub

**Secrets** (Settings, Secrets and variables, Actions) :

| Nom | Contenu |
|---|---|
| `MAIL_EXPEDITEUR` | l'adresse Gmail d'envoi |
| `MAIL_DESTINATAIRE` | l'adresse qui recoit |
| `MAIL_MOT_DE_PASSE` | les 16 lettres d'un mot de passe d'application Google, pas le mot de passe du compte |
| `URL_SUIVI` | l'adresse de la page Pages, ajoutee en bas des mails |

**Permissions** : Settings, Actions, General, Workflow permissions doit etre
sur **Read and write**, sans quoi le commit de fin de passage echoue.

**Pages** : Settings, Pages, Deploy from a branch, `main`, dossier `/ (root)`.
Le depot doit etre public, Pages n'etant gratuit que dans ce cas. Les secrets
restent chiffres, et les statuts de candidature ne quittent jamais le
navigateur.

**Depot endormi** : GitHub desactive les taches planifiees des depots sans
activite depuis soixante jours. Le commit automatique de fin de passage suffit
a l'eviter.

---

## 9. Diagnostic

Le journal est la premiere chose a lire : onglet **Actions**, dernier passage,
etape **Lancer la veille**. Il donne, ligne par ligne, chaque page interrogee,
chaque annonce retenue, et chaque annonce ecartee avec son motif en clair.

| Symptome | Piste |
|---|---|
| Coche rouge | l'erreur est en rouge dans l'etape qui a echoue |
| Echec au commit final | permissions du workflow en lecture seule |
| `Configuration mail incomplete` | un secret manque ou est mal nomme |
| `Envoi impossible` avec erreur d'authentification | le secret contient le mot de passe Gmail au lieu du mot de passe d'application |
| Mail « sources injoignables » | aucune page n'a repondu, souvent passager ; si cela dure, les URLs du site ont change |
| Un groupe remonte toujours zero | sa page de liste a change de nom, corriger `sources_jobijoba()` |
| Trop de faux positifs | le journal donne le motif de chaque rejet, c'est la que se regle le filtre en cause |
| La page de suivi reste vide | verifier qu'elle est ouverte en `https`, pas depuis un fichier local |

---

## 10. Limites assumees

- **Une seule source.** Si Jobijoba tombe ou change ses URLs, la veille
  s'arrete. Le mail « sources injoignables » sert d'alarme.
- **Un jour de decalage possible** avec les sites employeurs.
- **Les offres sans date sont perdues.** Choix delibere apres l'incident de
  l'annonce de 2024.
- **Les statuts ne sont pas sauvegardes ailleurs que dans le navigateur.**
  C'est le prix d'un suivi sans compte ni serveur. D'ou l'export.
- **Pas de detection des offres retirees.** Une annonce fermee reste dans le
  suivi jusqu'a ce qu'elle soit archivee a la main.
