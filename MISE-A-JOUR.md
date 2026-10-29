# Mettre a jour le depot veille-alternance

Ton depot existe deja, avec la version de septembre : l'ancien `veille.py`,
son workflow, et les fichiers du mode d'emploi local. Cette procedure remplace
ce qui doit l'etre, ajoute la page de suivi, et supprime le reste.

Compte vingt minutes. Rien ne tourne sur ta tablette, elle ne sert qu'a
l'installation puis a consulter.

**Conseil pour toute la procedure :** dans Chrome, menu a trois points, coche
**Site pour ordinateur**. L'interface GitHub mobile cache la moitie des boutons.

---

## Ce qui change par rapport a l'ancienne version

| Fichier | Quoi faire |
|---|---|
| `veille.py` | **remplacer** par le nouveau, entierement reecrit |
| `.github/workflows/veille.yml` | **remplacer** : un passage par jour a 8h, heure de Paris, ete comme hiver |
| `index.html` | **ajouter** : la page de suivi des candidatures |
| `offres.json` | **ajouter** : le pont entre la veille et la page de suivi |
| `etat.json` | **supprimer** : l'ancien format n'est plus lu, et les criteres ont change |
| `config.exemple.ini` | remplacer, ou laisser, il ne sert que hors GitHub |
| `GITHUB.md`, `LISEZMOI.md`, `lancer_veille.bat`, `tester.bat` | **supprimer** s'ils sont encore la, ils decrivent l'ancienne installation |
| `veille.log` | laisser, il sera complete |

Les secrets `MAIL_EXPEDITEUR`, `MAIL_DESTINATAIRE` et `MAIL_MOT_DE_PASSE` sont
deja en place et restent valables. Il n'y en a qu'un a ajouter, `URL_SUIVI`.

---

## Etape 1. Rendre le depot public

La page de suivi a besoin de GitHub Pages, et Pages n'est gratuit que sur un
depot public.

**Avant de basculer, verifie une chose :** ouvre le depot et cherche un fichier
`config.ini`. S'il existe, il contient ton mot de passe d'application Gmail en
clair. Dans ce cas, ne rends rien public : va d'abord sur
https://myaccount.google.com/apppasswords, supprime ce mot de passe, cree-en un
nouveau, mets-le dans le secret `MAIL_MOT_DE_PASSE`, puis supprime le fichier
du depot. Passer un depot en public expose aussi tout son historique, donc un
fichier supprime aujourd'hui reste lisible dans les anciens commits.

S'il n'y a pas de `config.ini`, tu peux y aller :

1. Onglet **Settings** du depot.
2. Tout en bas, section **Danger Zone**, ligne **Change repository visibility**.
3. **Change visibility**, puis **Make public**, et confirme en tapant le nom
   du depot.

Ce qui devient visible : le code, la liste des annonces publiques trouvees, et
le journal. Ce qui ne l'est pas : tes secrets, qui restent dans le coffre
chiffre, et tes statuts et notes de candidature, qui restent dans le navigateur
de ta tablette.

**Si tu preferes garder le depot prive**, c'est possible : la veille et les
mails fonctionnent pareil. Tu perds seulement la page de suivi hebergee, et il
faudra ouvrir `index.html` autrement. Dis-le-moi et je te donne le montage a
deux depots.

---

## Etape 2. Supprimer les fichiers de l'ancienne version

Pour chaque fichier a supprimer de la liste plus haut :

1. Clique sur le fichier dans le depot.
2. Bouton avec les trois points en haut a droite, **Delete file**.
3. En bas, **Commit changes**.

Commence par `etat.json`. C'est le plus important : il contient les annonces
deja signalees par l'ancienne version, dans un format que le nouveau script ne
lit plus, et avec des criteres qui ont change depuis. En le supprimant, tu
repars propre et le premier passage te remontera tout ce qui est ouvert
aujourd'hui.

---

## Etape 3. Deposer les nouveaux fichiers

1. **Add file**, puis **Upload files**.
2. Envoie `veille.py`, `index.html`, `offres.json` et `config.exemple.ini`.
   GitHub ecrase les fichiers de meme nom, c'est ce qu'on veut.
3. **Commit changes**.

Puis le workflow, qui est dans un sous-dossier et ne peut pas etre envoye de
la meme facon :

4. Ouvre `.github/workflows/veille.yml` dans le depot.
5. Icone **crayon** en haut a droite.
6. Selectionne tout l'ancien contenu, supprime-le, et colle le nouveau
   `veille.yml`.
7. **Commit changes**.

---

## Etape 4. Ajouter le secret de la page de suivi

1. **Settings**, menu de gauche, **Secrets and variables**, puis **Actions**.
2. **New repository secret**.

| Name | Secret |
|---|---|
| `URL_SUIVI` | `https://TON-PSEUDO.github.io/veille-alternance/` |

Remplace `TON-PSEUDO` par ton nom d'utilisateur GitHub, et `veille-alternance`
par le nom exact de ton depot s'il differe. Ce lien sert uniquement a mettre
l'adresse du suivi en bas de chaque mail.

Verifie au passage que les trois autres secrets sont toujours la.

---

## Etape 5. Publier la page de suivi

1. **Settings**, menu de gauche, **Pages**.
2. **Source** : `Deploy from a branch`.
3. **Branch** : `main`, dossier `/ (root)`. **Save**.
4. Attends deux ou trois minutes, rafraichis : GitHub affiche l'adresse de la
   page.

Ouvre-la sur la tablette et **ajoute-la a l'ecran d'accueil** (menu a trois
points de Chrome, « Ajouter a l'ecran d'accueil »). Elle s'ouvrira comme une
application.

Trois offres y sont deja, celles retenues en septembre, dont SPIE Thepault.

---

## Etape 6. Premier scan

1. Onglet **Actions**, colonne de gauche, **Veille alternance**.
2. A droite, **Run workflow**, puis **Run workflow** dans le petit menu.
3. Rafraichis. Le rond jaune devient une coche verte au bout de quelques
   minutes.

Clique sur la ligne, puis **scanner**, puis **Lancer la veille** pour derouler
le journal : chaque page interrogee, chaque annonce retenue, et chaque annonce
ecartee avec son motif.

Comme tu as supprime `etat.json`, ce passage repart de zero et sera le plus
long. Regarde ta boite mail, puis ta page de suivi : les nouvelles offres y
apparaissent toutes seules au chargement suivant.

Ensuite, plus rien a faire. Le scan part seul tous les jours a 8h, heure de
Paris, y compris apres les changements d'heure.

---

## Ce qui a change dans les criteres

L'ancienne version acceptait toute la Loire-Atlantique et ne connaissait pas
les metiers de l'energie. La nouvelle :

- **Lieu** : Nantes et sa proche peripherie seulement. Saint-Nazaire, Montoir,
  Donges, Ancenis et Chateaubriant sont ecartes.
- **Domaines** : quatre familles au lieu de trois. La nouvelle est
  performance energetique et EnR (audit, GTB, reseaux de chaleur,
  photovoltaique, eolien, hydrogene, decarbonation).
- **Filiales** : declarees explicitement, Omexom, Citeos, Dalkia,
  EDF Renouvelables, Engie Green, Equans, Clemessy et les autres.
- **Employeur** : lu dans le champ employeur de l'annonce et plus dans le bas
  de page, ce qui evite de prendre une banque pour la SNCF.
- **Age** : les annonces de plus de trente jours sont ignorees.
- **Panne** : si aucune source ne repond, le mail le dit clairement au lieu
  d'annoncer « rien de neuf ».

---

## Comment ca marche, en clair

Le script telecharge une trentaine de pages de liste, une par employeur et par
zone, sur Jobijoba. Il en extrait les adresses des annonces d'apres la forme
des URLs, et non d'apres la mise en page, ce qui le rend insensible aux
changements de design. Pour chaque annonce jamais vue, il ouvre la fiche et lit
le bloc de donnees structurees `JobPosting` que les sites emploi publient pour
Google : titre, employeur, lieu, date, description.

Il applique ensuite les filtres, dans cet ordre : employeur parmi les quatorze
groupes, contrat en alternance, commune acceptee, annonce de moins de trente
jours, metier qui n'est pas un poste d'execution, niveau Bac+4 ou Bac+5, et
domaine parmi les quatre familles.

Ce qui reste part par mail, est ajoute a `offres.json`, et apparait dans la
page de suivi. Les references traitees sont notees dans `etat.json` pour ne
jamais signaler deux fois la meme offre. Ces fichiers sont reecrits dans le
depot a chaque passage, ce qui garde aussi le depot actif : GitHub desactive
les taches planifiees des depots endormis depuis soixante jours.

Le script respecte le `robots.txt` de chaque site et attend une seconde entre
deux requetes. Cote facture, il n'y en a pas : GitHub Actions est gratuit et sans limite de
minutes pour un depot public.

---

## Le suivi de candidatures

Chaque offre a un statut : a etudier, a postuler, postule, relance, entretien,
accepte, refus, archive. Quand tu passes une offre a **Postule**, la date du
jour s'enregistre. Dix jours plus tard sans reponse, un bandeau te dit qui
relancer. Tu peux ajouter des notes, et saisir a la main une offre trouvee
ailleurs.

**Important** : tes statuts et tes notes vivent dans le navigateur de ta
tablette, pas sur GitHub. Ils survivent aux fermetures et aux redemarrages,
mais pas a un effacement des donnees de navigation ni a un changement
d'appareil. Le bouton **Exporter mes donnees**, en bas de la page, enregistre
un fichier de sauvegarde, et **Importer un fichier** le relit. Fais-le de temps
en temps.

---

## Modifier les criteres plus tard

Tout est en clair en haut de `veille.py`. Depuis la tablette : ouvre le fichier
dans le depot, icone crayon, modifie, **Commit changes**. Le passage suivant
utilise la nouvelle version.

| Je veux | Ou toucher |
|---|---|
| Elargir a Bac+3 | retire `bac+3`, `licence pro` et `bachelor` de `NIVEAU_KO` |
| Accepter Saint-Nazaire | retire les communes de `COMMUNES_KO`, ajoute-les a `COMMUNES_OK` |
| Ajouter un employeur | une entree dans `EMPLOYEURS` et une ligne dans `sources_jobijoba` |
| Accepter les stages | ajoute `stage` dans `MOTS_ALTERNANCE` |
| Voir aussi les fonctions support | vide la liste `DOMAINE_KO` |
| Remonter des annonces plus anciennes | augmente `AGE_MAX_JOURS` |
| Changer l'heure | `HEURE_PASSAGE` dans `veille.py`, et les deux lignes `cron` de `veille.yml` |

---

## Si ca coince

**La coche est rouge.** Clique dessus et deroule les etapes, l'erreur est en
rouge. Une erreur d'authentification SMTP veut presque toujours dire que
`MAIL_MOT_DE_PASSE` contient le mot de passe Gmail habituel au lieu des 16
lettres du mot de passe d'application.

**Erreur de push a la derniere etape du workflow.** Verifie dans **Settings**,
**Actions**, **General**, section **Workflow permissions**, que
**Read and write permissions** est coche.

**Vert mais pas de mail.** Normal s'il n'y a rien de nouveau : dans ce cas le
script n'ecrit que tous les sept jours. Regarde aussi les spams.

**Mail « sources injoignables ».** Aucune page n'a repondu. Souvent passager.
Si ca dure, envoie-moi le journal, je corrige les motifs d'extraction.

**La page de suivi reste vide ou n'enregistre rien.** Verifie que tu l'ouvres
bien par l'adresse `https://...github.io/...` et pas depuis un fichier
telecharge : Chrome refuse d'enregistrer les donnees d'une page ouverte en
local. Verifie aussi que tu n'es pas en navigation privee.

**Deux mails par passage.** La tache planifiee Claude tourne encore en
parallele. Dis-le-moi et je la desactive.

---

## Fichiers du depot, apres mise a jour

| Fichier | Role |
|---|---|
| `veille.py` | le programme |
| `.github/workflows/veille.yml` | la planification GitHub |
| `index.html` | la page de suivi des candidatures |
| `offres.json` | les offres retenues, ecrit par le script, lu par la page |
| `etat.json` | les annonces deja vues, recree automatiquement |
| `veille.log` | le journal de tous les passages |
| `config.exemple.ini` | modele de configuration, utile seulement hors GitHub |
