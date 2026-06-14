# 🏐 Gestionnaire de tournoi de volley

Une petite application pour organiser un tournoi de volley : on saisit les équipes,
l'outil génère les matchs, les répartit **en parallèle sur plusieurs terrains** (pour
que personne n'attende trop longtemps), calcule les classements, puis enchaîne sur une
**phase finale** (poule principale / consolante) et une **phase éliminatoire** (tableaux
avec petite finale).

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

Sur l'écran d'accueil, remplis le formulaire :
- **Nom du tournoi**
- **Nombre d'équipes**
- **Nombre de poules de classement** (les groupes pour la première phase)
- **Nombre de tours de brassage** (combien de fois on rebrasse les poules selon le niveau)
- **Nombre de terrains** disponibles (combien de matchs peuvent se jouer **en même temps**)
- **Points pour gagner un match** (ex. 25 — format « 1 set sec »)
- Les **noms des équipes** (un par ligne ; si tu laisses vide, elles s'appellent E1, E2, …)

Clique **🏐 Créer le tournoi**.

### b. Les tours de brassage

Pour chaque tour, l'outil affiche le **planning par vagues** : à chaque vague, jusqu'à N
matchs se jouent en parallèle (N = nombre de terrains), et **aucune équipe ne joue deux
fois dans la même vague**. La répartition est calculée pour **ne pas laisser une équipe trop
longtemps sans jouer**.

Tu saisis les **scores** au fur et à mesure (les points de chaque équipe). Le **classement**
se met à jour automatiquement. Quand tous les matchs d'un tour sont remplis, le bouton pour
**lancer le tour suivant** apparaît : les équipes sont alors **re-réparties selon le
classement** (les premières ensemble, les deuxièmes ensemble… = poules de niveau).

### c. Les finales : poule principale / consolante

Après le dernier tour de brassage, clique sur **générer les finales**. Selon le classement
général, les meilleures équipes vont en **poule principale**, les autres en **poule
consolante**. Chaque poule rejoue un mini-championnat, avec scores et classement comme avant.

### d. La phase éliminatoire

À la fin des finales, l'outil génère un **tableau à élimination directe pour chaque poule**.
Le placement (têtes de série) est fait pour que **le 1er et le 2e d'une poule ne puissent se
rencontrer qu'en finale**. Chaque tableau comporte une **petite finale** (match pour la 3e
place). À la fin, le **podium** s'affiche avec 🥇🥈🥉.

### e. Les réglages (barre latérale ⚙️)

Dans le panneau de gauche, tu peux ajuster **en cours de tournoi** :
- les points pour gagner un match,
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

Dans chaque onglet, le bouton d'impression génère une **feuille HTML** (planning des matchs +
classements). Ouvre le fichier puis fais `Cmd + P` (macOS) ou `Ctrl + P` (Windows) pour
imprimer ou enregistrer en PDF — pratique pour afficher le planning à côté des terrains.

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
│   ├── scheduler.py  #   répartition des matchs en parallèle sur les terrains
│   ├── bracket.py    #   tableaux à élimination directe + petite finale
│   ├── service.py    #   enchaînement des phases du tournoi
│   └── persistence.py#   sauvegarde / chargement JSON
├── test_engine.py    # tests automatiques du moteur
└── requirements.txt  # dépendances à installer
```

Pour lancer les tests du moteur :

```bash
.venv/bin/python test_engine.py
```
