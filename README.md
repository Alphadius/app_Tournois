# 🏐 Gestionnaire de tournoi de volley

Une petite application pour organiser un tournoi de volley : on saisit les équipes,
l'outil génère les matchs, les répartit **en parallèle sur plusieurs terrains** (pour
que personne n'attende trop longtemps), désigne automatiquement des **équipes arbitres**,
calcule les classements, puis enchaîne sur une **phase finale** (poule principale /
consolante jouées **en parallèle**) et une **phase éliminatoire** (tableaux avec petite
finale et podium).

Pour la phase de classement, tu choisis entre deux formats : des **poules de brassage**
(re-réparties par niveau à chaque tour) ou un **système suisse** (on oppose à chaque tour
des équipes de niveau proche, sans rejouer le même adversaire).

L'interface s'ouvre dans ton navigateur web, mais **tout tourne sur ta machine** : rien
n'est envoyé sur internet.

---

## 1. Avant de commencer (prérequis)

Tu as besoin de deux choses : **Python** et le **Terminal**. Pas de panique, c'est guidé.

### Python (version 3.10 ou plus récente)

Pour vérifier si tu l'as déjà, ouvre le **Terminal** :
- **macOS** : appuie sur `Cmd + Espace`, tape `Terminal`, puis `Entrée`.
- **Windows** : menu Démarrer → tape `PowerShell` → `Entrée`.

Dans la fenêtre noire qui s'ouvre, tape :

```bash
python3 --version
```

- Si ça affiche `Python 3.10.x` (ou plus, ex. `3.13.1`) → c'est bon, passe à l'étape 2.
- Si ça dit « command not found » ou une version trop ancienne → installe Python :
  - **macOS / Windows** : télécharge-le sur **https://www.python.org/downloads/** et installe-le
    (sous Windows, **coche la case « Add Python to PATH »** pendant l'installation).

### Git (pour récupérer le code)

Vérifie avec :

```bash
git --version
```

- Si une version s'affiche → c'est bon.
- Sinon → **macOS** : tape `xcode-select --install` puis valide. **Windows** : installe depuis
  **https://git-scm.com/download/win**.

---

## 2. Récupérer le projet

Dans le Terminal, place-toi là où tu veux ranger le projet (par ex. ton dossier personnel),
puis télécharge le code :

```bash
cd ~
git clone https://github.com/alphadius/app_Tournois.git
cd app_Tournois
```

> `cd ~` te met dans ton dossier personnel. `git clone` télécharge le projet dans un nouveau
> dossier `app_Tournois`. `cd app_Tournois` entre dans ce dossier. À partir d'ici, **toutes
> les commandes se tapent depuis ce dossier**.

---

## 3. Installer l'application

On crée un « environnement isolé » (un dossier `.venv` qui contient les dépendances, sans
toucher au reste de ta machine), puis on installe ce qu'il faut.

**Sur macOS / Linux :**

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

**Sur Windows (PowerShell) :**

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

L'installation prend quelques dizaines de secondes (elle télécharge Streamlit, la librairie
qui affiche l'interface). C'est à faire **une seule fois**.

---

## 4. Lancer l'application

**Sur macOS / Linux :**

```bash
.venv/bin/streamlit run app.py
```

**Sur Windows (PowerShell) :**

```powershell
.venv\Scripts\streamlit run app.py
```

Ton navigateur s'ouvre tout seul sur l'application (adresse `http://localhost:8501`).
Si ce n'est pas le cas, ouvre cette adresse à la main.

> ℹ️ Au tout premier lancement, Streamlit peut demander une adresse e-mail dans le Terminal :
> tu peux **laisser vide et appuyer sur `Entrée`**, ce n'est pas obligatoire.

**Pour arrêter l'application** : reviens dans le Terminal et appuie sur `Ctrl + C`.

**Pour la relancer plus tard** : ouvre le Terminal, puis :

```bash
cd ~/app_Tournois
.venv/bin/streamlit run app.py
```

(Pas besoin de refaire l'installation, juste cette commande.)

---

## 5. Comment utiliser l'outil

### a. Créer un tournoi

Sur l'écran d'accueil, choisis d'abord le **système de la phase de classement** :
**poules de brassage** ou **système suisse**. Le formulaire s'adapte ensuite.

Champs communs :
- **Nom du tournoi**
- **Nombre d'équipes**
- **Nombre de terrains** disponibles (combien de matchs peuvent se jouer **en même temps**)
- **Points pour gagner un match**, réglables **par phase** : brassage / suisse (ex. 15),
  poule principale / consolante (ex. 21), élimination directe (ex. 25). C'est un format
  « 1 set sec » : tu saisis les points marqués, le vainqueur est celui qui en a le plus.
- Les **noms des équipes** (un par ligne ; si tu laisses vide, elles s'appellent E1, E2, …)

En **poules de brassage**, tu définis en plus :
- la **répartition des poules**, au choix : soit **par nombre de poules**, soit **par nombre
  d'équipes par poule**. Si le total n'est pas un multiple, l'outil équilibre tout seul
  (ex. 10 équipes / 4 par poule → 3 poules de 4, 3 et 3) — pas de poule isolée ;
- le **nombre de tours de brassage** (combien de fois on rebrasse les poules selon le niveau).

En **système suisse**, tu choisis le **nombre de tours** : *illimité* (on enchaîne jusqu'à
ce qu'une seule équipe reste invaincue) ou *fixé* (utile quand le temps est compté).

Dans tous les cas (brassage **ou** suisse), tu règles aussi la **phase finale** :
- **Poules par groupe final** : combien de poules pour la principale **et** pour la
  consolante. `1` (par défaut) = une seule grande poule par groupe (tout le monde s'affronte,
  mais ça peut être long). Plus de poules = moins de matchs par équipe ; les équipes sont
  réparties en **poules de niveau** d'après le classement de fin de phase de classement ;
- **Départ du tableau à élimination directe** : à quel tour commence l'élimination de chaque
  groupe — **8e de finale** (16 équipes), **quart** (8), **demi** (4) ou **finale** (2). Le
  nombre de qualifiés en découle directement et ils sont pris **équitablement dans chaque
  poule** (ex. 2 poules + départ en quart → les 4 premiers de chaque poule). S'il n'y a pas
  assez d'équipes dans le groupe, l'outil **démarre automatiquement à un tour plus avancé**.

Clique **🏐 Créer le tournoi**. Un bouton **↩️ Reprendre le dernier tournoi** est aussi
proposé si une sauvegarde automatique existe.

### b. La phase de classement (brassage ou suisse)

Pour chaque tour, l'outil affiche le **planning par vagues** : à chaque vague, jusqu'à N
matchs se jouent en parallèle (N = nombre de terrains), et **aucune équipe ne joue deux
fois dans la même vague**. La répartition est calculée pour **ne pas laisser une équipe trop
longtemps sans jouer**. Chaque match se voit attribuer une **équipe arbitre** parmi celles
qui ne jouent pas à ce moment-là, répartie de façon **équitable**.

Tu saisis les **scores** au fur et à mesure (les points de chaque équipe). Le **classement**
se met à jour automatiquement. Quand tous les matchs d'un tour sont remplis, le bouton pour
**lancer le tour suivant** apparaît :
- en **poules** : les équipes sont **re-réparties selon le classement** (les premières
  ensemble, les deuxièmes ensemble… = poules de niveau) ;
- en **suisse** : on apparie les équipes de classement proche, **sans rejouer un adversaire
  déjà rencontré** (avec un nombre impair d'équipes, l'une est exemptée à tour de rôle et
  marque une victoire).

> ℹ️ Dès que tu génères une nouvelle phase (tour suivant, finales, élimination), l'outil
> **bascule automatiquement** sur cette phase et **remonte en haut de la page** — tu te
> retrouves directement devant le planning qui va se jouer, sans avoir à chercher l'onglet.
> Tu peux toujours revenir sur une phase précédente avec le **sélecteur de phases** en haut.

### c. Les finales : poule principale / consolante

Après la phase de classement, clique sur **générer les finales**. Le classement général est
**coupé en deux** : la **moitié haute** va en **principale**, la **moitié basse** en
**consolante**. Selon le réglage **Poules par groupe final** (choisi à la création) :
- avec **1 poule par groupe** : chaque groupe est un seul mini-championnat (« Principale »,
  « Consolante »), tout le monde s'affronte ;
- avec **plusieurs poules par groupe** : chaque groupe est re-divisé en **poules de niveau**
  équilibrées (« Principale A », « Principale B »…), ce qui réduit le nombre de matchs.

Les poules finales se jouent **en parallèle, chaque poule sur son propre terrain** : avec
par ex. **4 poules et 4 terrains**, chaque poule occupe un terrain dédié et déroule son
mini-championnat de bout en bout sans attendre les autres (fini les longues attentes où une
poule enchaîne tous ses matchs pendant que les autres patientent). Quand il y a **plus de
terrains que de poules**, les terrains en surplus accélèrent les premières poules (2 matchs
de front) ; quand il y a **plus de poules que de terrains**, les poules sont traitées par
**lots successifs**. Principale et consolante sont **entrelacées** pour avancer ensemble.
Chaque match est arbitré **en priorité** par une équipe **de la même compétition** ; si
aucune n'est libre à ce moment-là, une équipe de l'autre compétition prend le relais, et si
vraiment personne n'est disponible le match est indiqué en **arbitrage auto-géré**.

### d. La phase éliminatoire

À la fin des finales, l'outil génère **un tableau à élimination directe par groupe**
(principale, consolante). Le tableau démarre au **tour choisi à la création** (8e, quart, demi
ou finale) : on retient les **meilleurs du groupe** (répartis équitablement entre les poules —
tous les 1ers d'abord, puis les 2es, etc.). S'il n'y a pas assez d'équipes, le tableau démarre
**automatiquement à un tour plus avancé**. Le placement (têtes de série) est fait pour que
**le 1er et le 2e ne puissent se rencontrer qu'en finale**. Chaque tableau comporte une
**petite finale** (match pour la 3e place), et les arbitres viennent **en priorité** de la
**même compétition** (à défaut, une équipe de l'autre compétition dépanne ; si aucune n'est
libre, l'arbitrage est **auto-géré**). À la fin, le **podium** s'affiche avec 🥇🥈🥉.

Les deux tableaux (principale et consolante) sont ordonnancés **en parallèle** : les terrains
sont **répartis entre les deux compétitions** (ex. 4 terrains = 2 pour la principale, 2 pour
la consolante) et leurs premiers tours **démarrent en même temps**. Fini « tous les quarts de
la principale, puis tous les quarts de la consolante » — les deux brackets avancent ensemble.
Comme pour les poules, un tour ne commence qu'une fois le précédent terminé (les équipes
qualifiées doivent être connues).

### e. Les réglages (barre latérale ⚙️)

Dans le panneau de gauche, tu peux ajuster **en cours de tournoi** :
- les points pour gagner un match, **par phase** (brassage/suisse, finales, élimination),
- les points attribués par victoire / défaite,
- l'ordre des **critères de départage** (points, confrontation directe, ratio de points, ratio de sets),
- afficher ou non la colonne **Δpts**.

Les classements se recalculent automatiquement à partir des scores déjà saisis.

### f. Sauvegarde

- **Sauvegarde automatique** : après chaque action, l'état complet est enregistré dans
  `.autosave/dernier.json` (sur ta machine). Si tu fermes l'onglet et reviens, le tournoi est
  **restauré tout seul**.
- **Sauvegarde manuelle** : le bouton **💾 télécharger** (barre latérale) crée un fichier
  `.json` à l'endroit de ton choix — pratique pour garder une copie ou la transférer.
- **Reprendre une sauvegarde** : utilise **📂 charger** pour ré-ouvrir un `.json` enregistré.

### g. Impression du planning et des feuilles de match

Dans chaque onglet, le bouton **🖨️ Planning imprimable** génère une **feuille HTML** (planning
des matchs avec terrain, **arbitre** et points cible, + classements). Ouvre le fichier puis fais
`Cmd + P` (macOS) ou `Ctrl + P` (Windows) pour imprimer ou enregistrer en PDF — pratique
pour afficher le planning à côté des terrains.

Le bouton **📝 Feuilles de match** produit, lui, **une feuille par rencontre** à distribuer
sur chaque terrain. Chaque feuille indique les **deux équipes**, l'**arbitre**, le **terrain**,
les **points cible**, une **grille de cases à cocher** pour pointer le score au fur et à mesure,
et une **zone de score final** (+ vainqueur). 
- Pour les phases dont tous les matchs sont connus d'avance (brassage, tour suisse, poules
  finales), le bouton télécharge **toutes les feuilles d'un coup, à raison de 2 par page**.
- Pour la phase éliminatoire, où les matchs se débloquent au fur et à mesure, un bouton
  **📝 Feuille de match** apparaît **sous chaque rencontre dès qu'elle est jouable** (les deux
  équipes connues) pour imprimer cette feuille-là.

### h. Le bilan du tournoi (statistiques)

À la fin (onglet **Élimination**) ou à tout moment depuis la barre latérale, le bouton
**📊 Bilan du tournoi** télécharge une **feuille HTML récapitulative** :
- les **chiffres clés** : équipes, matchs joués, points et sets joués, vagues, moyenne de
  points par match, marge moyenne de victoire ;
- les **podiums** (🥇🥈🥉) de chaque poule finale ;
- des **faits marquants** : plus large victoire, match le plus serré, match le plus
  prolifique, meilleure attaque, meilleure défense, équipe qui a le plus arbitré ;
- un **bilan par phase** (matchs et points) ;
- le **classement complet des équipes** (joués, victoires, défaites, points marqués /
  encaissés, différence, nombre de matchs arbitrés). Ce classement **respecte les groupes
  finals** : toutes les équipes de la **principale** sont classées avant celles de la
  **consolante** (une équipe de consolante ne peut pas devancer une équipe de principale),
  une colonne **Groupe** le rappelle.

Comme pour le planning, ouvre le fichier puis `Cmd/Ctrl + P` pour l'imprimer ou le garder en PDF.

### i. Diffuser le planning en ligne (page publique en lecture seule)

Tu peux donner aux participants un **lien web** qui montre, en direct, les **matchs en cours**,
les **prochains matchs**, le **classement** et, en phase finale, les **tableaux d'élimination**
(principale **et** consolante, avec les scores) — **sans** qu'ils puissent rien modifier.

#### Comment ça marche (le principe)

Il y a **deux apps** et **un fichier-relais** en ligne :

```
  Ton ordi (app.py)  ── écrit ──►  Gist GitHub  ── lit ──►  Page publique (public.py)
   [avec ton token]                (tournoi.json)            [aucun token, lecture seule]
```

- **`app.py`** tourne sur **ta** machine (saisie des scores) et **publie** l'état du tournoi
  dans un **Gist GitHub** (un petit fichier en ligne), grâce à un **token** qui ne quitte
  jamais ton ordinateur.
- **`public.py`** est déployée sur **Streamlit Community Cloud** : elle **lit** ce fichier et
  l'affiche. Comme elle n'a **aucun** champ de saisie ni token, les participants ne peuvent
  rien modifier — c'est garanti par construction.

> Il faut une connexion internet sur ta machine pour publier. Sans réseau, l'app locale
> continue de fonctionner normalement ; seule la page en ligne cesse de se mettre à jour.

#### Mise en place (une seule fois, ~15 min)

**Étape 1 — Créer le Gist (le fichier-relais)**
1. Va sur [gist.github.com](https://gist.github.com) (connecte-toi à ton compte GitHub).
2. Nom du fichier : **`tournoi.json`** — contenu : **`{}`**.
3. Bouton en bas → **« Create public gist »** (⚠️ **public**, pas *secret* : sinon la lecture
   sans token ne marchera pas).
4. Dans l'URL de la page, repère :
   - ton **login GitHub** (ex. `TON_LOGIN`) ;
   - l'**ID du Gist** = la longue suite de caractères, **sans rien d'autre**.
     L'URL ressemble à `https://gist.github.com/TON_LOGIN/abcdef0123456789…` →
     l'ID est `abcdef0123456789…`.
   - ⚠️ **Piège fréquent :** ne copie **pas** un morceau qui contient `#file-tournoi-json`
     (c'est une ancre de la page, pas l'ID). L'ID ne contient **jamais** de `#`.

**Étape 2 — Créer le token GitHub (le « mot de passe » d'écriture)**
1. [github.com/settings/tokens](https://github.com/settings/tokens) → bouton
   **« Generate new token »** → choisis bien **« Generate new token (classic) »**.
   - ⚠️ **Pas** le type *fine-grained* (celui qui demande « public/all/select repositories ») :
     il **ne gère pas** les Gists. Le type *classic* propose une liste de cases à cocher.
2. **Note** : `tournoi-volley` — **Expiration** : une date après ton tournoi.
3. **Select scopes** : coche **uniquement** la case **`gist`**.
4. **Generate token** → copie le token (`ghp_…`) **tout de suite** (il ne s'affiche qu'une fois).

**Étape 3 — Configurer ta machine**
1. Copie le modèle de secrets :
   ```bash
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   ```
2. Ouvre `.streamlit/secrets.toml` et renseigne **tes** valeurs :
   ```toml
   GIST_ID = "abcdef0123456789..."     # l'ID seul, SANS #file-...
   GIST_USER = "TON_LOGIN"
   GIST_TOKEN = "ghp_xxxxxxxxxxxx"      # reste sur ta machine, jamais en ligne
   ```
   > Ce fichier est **ignoré par git** (voir `.gitignore`) : ton token ne partira jamais sur
   > GitHub, même si ton dépôt est public.

**Étape 4 — Rendre le dépôt accessible à Streamlit**

Streamlit Community Cloud doit pouvoir lire le code. Deux possibilités :
- **Dépôt privé** : au moment de te connecter sur Streamlit, autorise l'accès à tes dépôts
  privés (via la *GitHub App* « Streamlit Community Cloud » → *Configure* → ajoute le dépôt).
- **Dépôt public** (le plus simple) : *Settings* du dépôt → *Danger Zone* →
  *Change repository visibility* → *Public*. C'est **sans risque** ici : aucun secret n'est
  versionné (le `secrets.toml` est ignoré, et le code ne contient aucun token).

**Étape 5 — Déployer la page publique**
1. Va sur [share.streamlit.io](https://share.streamlit.io) → connecte-toi avec GitHub.
2. **« Create app »** → **« Deploy a public app from GitHub »**.
3. Renseigne :
   - **Repository** : `TON_LOGIN/app_Tournois`
   - **Branch** : `main`
   - **Main file path** : **`public.py`**  ⚠️ (bien `public.py`, **pas** `app.py`)
4. **« Advanced settings… »** → **Secrets** → colle **uniquement** (⚠️ **jamais** le token) :
   ```toml
   GIST_ID = "abcdef0123456789..."
   GIST_USER = "TON_LOGIN"
   ```
5. **« Deploy »** → patiente 1-2 min → tu obtiens une URL `https://ton-app.streamlit.app`.
6. *(facultatif)* Mets cette URL dans `APP_PUBLIQUE_URL` de ton `secrets.toml` **local**
   (décommente la ligne) pour l'afficher en clair dans la barre latérale de ton app.

#### Au quotidien (le jour du tournoi)

1. Lance ton app : `.venv/bin/streamlit run app.py`.
2. Barre latérale → section **« 📡 Diffusion en ligne »** → coche **« Publier le planning en
   ligne »** (une seule fois). Tu peux aussi forcer un envoi avec **« Publier maintenant »**.
3. Partage l'URL `https://ton-app.streamlit.app` aux participants (lien, QR code…).
4. À chaque score saisi, la page publique se met à jour automatiquement en **~20 s**.

#### En cas de souci

| Symptôme | Cause / solution |
|---|---|
| Page publique bloquée sur « En attente de données… » | `GIST_ID` ou `GIST_USER` faux **dans les Secrets de Streamlit Cloud** (pas le fichier local !). Vérifie surtout que `GIST_ID` ne contient **pas** `#file-…`. Corrige puis *Reboot app*. |
| « Échec de la publication » côté app locale | Token mal copié, scope `gist` non coché, ou pas d'internet. Recrée le token (étape 2). |
| La case « 📡 Publier » n'apparaît pas | `secrets.toml` manquant ou incomplet (`GIST_ID` + `GIST_TOKEN` requis). Relance l'app après l'avoir rempli. |
| Le lien dans la barre latérale ne s'affiche pas | La ligne `APP_PUBLIQUE_URL` est restée **commentée** (`#`) — enlève le `#` et relance l'app. |
| Le classement n'apparaît pas en ligne | Mets à jour le code en ligne : `git push` (Streamlit redéploie tout seul), ou *Reboot app*. |
| `git push` → « Everything up-to-date » alors que tu as ajouté un fichier | `git add` ne suffit pas : il faut **committer** (`git commit -m "..."`) avant de pousser. |
| `git push` → « rejected … fetch first » | Le distant a des commits que tu n'as pas. Fais `git pull --rebase origin main` puis `git push`. |
| Erreur au déploiement Streamlit | Vérifie **Main file path = `public.py`** et que le code est bien **poussé** sur GitHub. |
| Léger décalage du planning/classement | Normal : ~20 s (rafraîchissement + cache GitHub). |

---

## 6. En cas de souci

- **« command not found: python3 »** → Python n'est pas installé ou pas dans le PATH (revois l'étape 1).
- **L'installation échoue avec « externally-managed-environment »** → tu as oublié de créer le
  `.venv` ; refais l'étape 3 (l'environnement isolé est obligatoire).
- **Le navigateur ne s'ouvre pas** → ouvre manuellement **http://localhost:8501**.
- **Une erreur après une mise à jour du code** → ferme l'app (`Ctrl + C`), clique sur
  **« Nouveau tournoi »** dans l'app, ou supprime le dossier `.autosave/`, puis relance.

---

## 7. Structure du projet (pour les curieux)

```
app_Tournois/
├── app.py            # l'interface Streamlit (ce que tu vois dans le navigateur)
├── public.py         # page publique en lecture seule (planning + classement en ligne)
├── sync.py           # publication / lecture du tournoi via un Gist GitHub
├── printview.py      # génération de la feuille de planning imprimable
├── engine/           # le « moteur » du tournoi (indépendant de l'interface)
│   ├── models.py     #   équipes, matchs, poules, règles de score
│   ├── ranking.py    #   calcul des classements et départages
│   ├── scheduler.py  #   répartition des matchs en parallèle + arbitres
│   ├── suisse.py     #   appariements du système suisse
│   ├── bracket.py    #   tableaux à élimination directe + petite finale
│   ├── service.py    #   enchaînement des phases du tournoi
│   ├── stats.py      #   bilan chiffré de fin de tournoi
│   └── persistence.py#   sauvegarde / chargement JSON
├── test_engine.py    # tests automatiques du moteur
└── requirements.txt  # dépendances à installer
```

Pour lancer les tests du moteur :

```bash
.venv/bin/python test_engine.py
```
