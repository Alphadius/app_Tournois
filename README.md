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
- **Qualifiés / poule → tableau** : quand il y a plusieurs poules par groupe, combien
  d'équipes de chaque poule rejoignent le **tableau à élimination directe** du groupe.

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

Les deux compétitions se déroulent **en parallèle sur des terrains dédiés** (par ex. avec 4
terrains : 2 pour la principale, 2 pour la consolante ; avec un nombre impair, le terrain en
plus alterne entre les deux). Chaque match est arbitré **en priorité** par une équipe **de la
même compétition** ; si aucune n'est libre à ce moment-là, une équipe de l'autre compétition
prend le relais, et si vraiment personne n'est disponible le match est indiqué en **arbitrage
auto-géré**.

### d. La phase éliminatoire

À la fin des finales, l'outil génère **un tableau à élimination directe par groupe**
(principale, consolante). S'il y avait **une seule poule** par groupe, tout le monde entre dans
le tableau ; s'il y avait **plusieurs poules**, seuls les **meilleurs de chaque poule** (selon
le réglage *Qualifiés / poule → tableau*) se rejoignent dans **un unique tableau** par groupe,
classés par tête de série (tous les 1ers de poule d'abord, puis les 2es, etc.). Le placement
est fait pour que **le 1er et le 2e ne puissent se rencontrer qu'en finale**. Chaque tableau
comporte une **petite finale** (match pour la 3e place), et les arbitres viennent **en
priorité** de la **même compétition** (à défaut, une équipe de l'autre compétition dépanne ;
si aucune n'est libre, l'arbitrage est **auto-géré**). À la fin, le **podium** s'affiche
avec 🥇🥈🥉.

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

### g. Impression du planning

Dans chaque onglet, le bouton d'impression génère une **feuille HTML** (planning des matchs
avec terrain, **arbitre** et points cible, + classements). Ouvre le fichier puis fais
`Cmd + P` (macOS) ou `Ctrl + P` (Windows) pour imprimer ou enregistrer en PDF — pratique
pour afficher le planning à côté des terrains.

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
  encaissés, différence, nombre de matchs arbitrés).

Comme pour le planning, ouvre le fichier puis `Cmd/Ctrl + P` pour l'imprimer ou le garder en PDF.

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
