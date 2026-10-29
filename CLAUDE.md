# CLAUDE.md

## Le projet

Veille d'offres d'alternance ingenieur a Nantes pour Marin, eleve ingenieur au
Cnam. Deux pieces, sans serveur ni IA a l'execution :

- `veille.py` : lance chaque jour a 8h, heure de Paris, par GitHub Actions
  (`.github/workflows/veille.yml`, crons 06:00 et 07:00 UTC, `heure_de_passer()`
  choisit). Il lit les pages de liste Jobijoba et HelloWork des quatorze groupes
  suivis et de leurs filiales, ouvre chaque fiche jamais vue, lit son bloc
  JSON-LD `JobPosting`, filtre (employeur, contrat, lieu, date, metier, niveau,
  domaine), ecrit `etat.json` et `offres.json`, puis envoie un mail via SMTP Gmail.
- `index.html` : page de suivi des candidatures servie par GitHub Pages. Elle lit
  `offres.json` et garde statuts et notes dans le `localStorage` du navigateur.

Une seule dependance : `requests`. `README.md` est la description complete et
fait reference ; sa section 6 liste les faux positifs deja corriges, a ne pas
reintroduire.

## Commandes

```
python test_filtres.py          rejoue les cas de test des filtres
python veille.py --test         passage complet sans mail ni ecriture de fichier
python veille.py --force-mail   envoie meme s'il n'y a rien de neuf
```

Sous Windows, installer aussi `tzdata` (`pip install tzdata`) : sans lui,
`ZoneInfo("Europe/Paris")` echoue, le script retombe sur l'UTC et les tests
d'horaire echouent. Sur GitHub Actions (Ubuntu), rien a faire.

`test_filtres.py` affiche `RATE` pour un cas en echec mais sort toujours avec
le code 0 : lire la sortie, pas seulement le code de retour.

## Regles de travail

- Apres toute modification des filtres, lancer `python test_filtres.py`, et
  ajouter un cas de test pour chaque nouveau faux positif.
- Ne jamais committer de `config.ini` ni de mot de passe : le depot est public,
  les identifiants vivent dans les secrets GitHub.
- `etat.json`, `offres.json` et `veille.log` sont reecrits par le commit
  automatique de fin de passage : eviter de les modifier a la main.

## Preferences de Marin

- Repondre en francais.
- Ne jamais utiliser de tiret long (cadratin), ni dans les reponses, ni dans le
  code, les mails ou la documentation. Utiliser virgules, deux-points ou
  parentheses.
- Un seul mail propre par passage : jamais de second mail correctif ou de
  doublon. Le mail doit etre juste du premier coup (texte via `set_content`,
  HTML via `add_alternative`).
