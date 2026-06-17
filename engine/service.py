"""Opérations de haut niveau : création du tournoi, tours de brassage et
re-répartition, poules finales, phase éliminatoire. API utilisée par l'UI.

Déroulé d'un tournoi :
  1. tour de brassage 1 (poules de classement)            -> classement
  2. (optionnel) re-répartition + tour de brassage 2..N    -> classement
  3. poule principale + poule consolante                   -> classement
  4. phase éliminatoire : un bracket par groupe            -> vainqueur
"""
from __future__ import annotations

from .bracket import generer_bracket, propager_vainqueur
from .models import Equipe, Phase, Poule, ReglesScore, Tournoi, creer_equipes
from .ranking import LigneClassement, classement_poule
from .scheduler import (
    assigner_arbitres, assigner_arbitres_elimination, generer_matchs_phase,
    generer_matchs_poule, generer_matchs_poules, ordonnancer,
    ordonnancer_elimination, ordonnancer_elimination_parallele,
    ordonnancer_poules_paralleles,
)

_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _est_suisse(t: Tournoi) -> bool:
    # getattr : tolère un objet d'une version antérieure (rechargement à chaud).
    return getattr(t, "systeme", "poules") == "suisse"


# --------------------------------------------------------------------------- #
#  Répartition
# --------------------------------------------------------------------------- #
def repartir_serpentin(equipes: list[Equipe], nb_poules: int) -> list[list[Equipe]]:
    """Répartit les équipes en `nb_poules` paquets équilibrés (système serpentin).

    Exemple 8 équipes / 2 poules -> [1,4,5,8] et [2,3,6,7].
    Appliqué à un classement, ça étale les meilleures équipes sur des poules
    différentes (chaque poule reçoit un mélange de niveaux).
    """
    paquets: list[list[Equipe]] = [[] for _ in range(nb_poules)]
    sens = 1
    i = 0
    for e in equipes:
        paquets[i].append(e)
        if sens == 1 and i == nb_poules - 1:
            sens = -1
        elif sens == -1 and i == 0:
            sens = 1
        else:
            i += sens
    return paquets


def tailles_poules(nb_equipes: int, nb_poules: int) -> list[int]:
    """Tailles des poules après répartition serpentin (équilibrées à 1 près).

    Ex : 10 équipes / 3 poules -> [4, 3, 3]. Sert d'aperçu dans l'UI.
    """
    if nb_poules < 1 or nb_equipes < 0:
        return []
    q, r = divmod(nb_equipes, nb_poules)
    return [q + 1] * r + [q] * (nb_poules - r)


def nb_poules_pour_taille(nb_equipes: int, equipes_par_poule: int) -> int:
    """Déduit un nombre de poules ÉQUILIBRÉES à partir d'une taille de poule visée.

    On arrondit au plus proche (0,5 -> au-dessus) et on garantit au moins 2 équipes
    par poule. Même si le nombre d'équipes n'est pas un multiple de la taille visée
    (erreur de saisie fréquente), la répartition serpentin produit ensuite des
    poules équilibrées (tailles différant d'au plus 1) — pas de poule isolée.

    Ex : 10 équipes, 4 par poule -> 3 poules (4, 3, 3) ; 9 équipes, 4 par poule
    -> 2 poules (5, 4).
    """
    if equipes_par_poule < 2:
        raise ValueError("Il faut au moins 2 équipes par poule.")
    if nb_equipes < 2:
        return 1
    from math import floor
    k = floor(nb_equipes / equipes_par_poule + 0.5)
    return max(1, min(k, nb_equipes // 2))


def _creer_poules_brassage(t: Tournoi, paquets: list[list[Equipe]], tour: int) -> None:
    for idx, paquet in enumerate(paquets):
        t.poules.append(Poule(
            nom=f"T{tour} · Poule {_ALPHABET[idx]}",
            phase=Phase.BRASSAGE, equipes=paquet, tour=tour))


def _creer_poules_groupe(t: Tournoi, equipes: list[Equipe], phase: Phase,
                         base_nom: str, nb_poules: int) -> None:
    """Crée les poules d'un groupe final (principale / consolante).

    Avec une seule poule, on garde le nom historique (`base_nom`, ex "Principale")
    pour la rétro-compatibilité. Avec plusieurs poules, on répartit les équipes en
    serpentin sur le classement (poules de niveau équilibrées) et on les nomme
    "Principale A", "Principale B"… Le nombre de poules est borné pour garantir au
    moins 2 équipes par poule.
    """
    nb = max(1, min(nb_poules, max(1, len(equipes) // 2)))
    if nb <= 1:
        t.poules.append(Poule(nom=base_nom, phase=phase, equipes=equipes))
        return
    for idx, paquet in enumerate(repartir_serpentin(equipes, nb)):
        t.poules.append(Poule(
            nom=f"{base_nom} {_ALPHABET[idx]}", phase=phase, equipes=paquet))


def _qualifies_pour_tableau(t: Tournoi, poules: list[Poule], cible: int) -> list[Equipe]:
    """Sélectionne au plus `cible` équipes pour le tableau à élimination directe,
    réparties équitablement entre les poules du groupe.

    On procède « par rang » : tous les 1ers de poule d'abord (du meilleur au moins
    bon), puis tous les 2es, etc., jusqu'à atteindre `cible`. Au sein d'un même rang,
    on départage par points de classement puis par différence de points marqués. Avec
    2 poules et une cible de 8, on prend ainsi les 4 premiers de chaque poule ; avec
    une seule poule, on prend simplement les `cible` premiers du classement.
    """
    classements = [classement_poule(p, t.matchs, t.regles) for p in poules]
    max_rang = max((len(c) for c in classements), default=0)
    ordre: list[Equipe] = []
    for rang in range(max_rang):
        rangees = [c[rang] for c in classements if rang < len(c)]
        rangees.sort(key=lambda l: (l.points, l.ratio_points), reverse=True)
        for ligne in rangees:
            ordre.append(ligne.equipe)
            if len(ordre) >= cible:
                return ordre
    return ordre


# --------------------------------------------------------------------------- #
#  Création
# --------------------------------------------------------------------------- #
def creer_tournoi(
    nom: str,
    noms_equipes: list[str],
    nb_poules: int,
    nb_terrains: int,
    nb_tours_brassage: int = 1,
    regles: ReglesScore | None = None,
    qualifies_principale_par_poule: int = 1,
    nb_poules_finales: int = 1,
    elim_taille_tableau: int = 8,
    systeme: str = "poules",
    suisse_nb_tours: int = 0,
) -> Tournoi:
    equipes = creer_equipes(noms_equipes)
    if len(equipes) < 2:
        raise ValueError("Il faut au moins 2 équipes.")
    if systeme not in ("poules", "suisse"):
        raise ValueError("Système de classement inconnu.")
    if systeme == "poules" and (nb_poules < 1 or nb_poules > len(equipes)):
        raise ValueError("Nombre de poules invalide.")
    if systeme == "poules" and nb_tours_brassage < 1:
        raise ValueError("Il faut au moins 1 tour de brassage.")
    if systeme == "suisse" and suisse_nb_tours < 0:
        raise ValueError("Nombre de tours suisse invalide.")
    if nb_poules_finales < 1:
        raise ValueError("Nombre de poules finales invalide.")
    if elim_taille_tableau < 2:
        raise ValueError("Taille du tableau d'élimination invalide.")

    t = Tournoi(
        nom=nom,
        nb_terrains=nb_terrains,
        regles=regles or ReglesScore(),
        equipes=equipes,
        nb_poules=nb_poules,
        nb_tours_brassage=nb_tours_brassage,
        qualifies_principale_par_poule=qualifies_principale_par_poule,
        nb_poules_finales=nb_poules_finales,
        elim_taille_tableau=elim_taille_tableau,
        systeme=systeme,
        suisse_nb_tours=suisse_nb_tours,
    )
    if systeme == "poules":
        _creer_poules_brassage(t, repartir_serpentin(equipes, nb_poules), tour=1)
    return t


# --------------------------------------------------------------------------- #
#  Tours de brassage
# --------------------------------------------------------------------------- #
def lancer_tour_brassage(t: Tournoi, tour: int) -> None:
    """Génère et ordonnance les matchs d'un tour de classement (poules ou suisse)."""
    if _est_suisse(t):
        from .suisse import generer_tour_suisse
        generer_tour_suisse(t, tour)
        return
    if t.matchs_tour(tour):
        return  # déjà lancé
    poules = t.poules_tour(tour)
    matchs = generer_matchs_poules(t, poules)
    ordonnancer(matchs, t.nb_terrains)
    t.matchs.extend(matchs)
    assigner_arbitres(t, matchs)


def tour_brassage_termine(t: Tournoi, tour: int) -> bool:
    matchs = t.matchs_tour(tour)
    return bool(matchs) and all(m.joue for m in matchs)


def classements_tour(t: Tournoi, tour: int) -> dict[str, list[LigneClassement]]:
    return {p.nom: classement_poule(p, t.matchs, t.regles) for p in t.poules_tour(tour)}


def classement_global_tour(t: Tournoi, tour: int) -> list[Equipe]:
    """Classement global d'un tour : on prend le 1er de chaque poule, puis tous
    les 2es, etc., chaque "rang" étant trié par points puis différence de points.
    Sert à re-répartir les équipes pour le tour suivant et à départager.
    """
    par_poule = classements_tour(t, tour)
    lignes_par_rang: dict[int, list[LigneClassement]] = {}
    for lignes in par_poule.values():
        for rang, ligne in enumerate(lignes):
            lignes_par_rang.setdefault(rang, []).append(ligne)

    ordre: list[Equipe] = []
    for rang in sorted(lignes_par_rang):
        groupe = sorted(lignes_par_rang[rang],
                        key=lambda l: (l.points, l.ratio_points), reverse=True)
        ordre.extend(l.equipe for l in groupe)
    return ordre


def generer_tour_brassage_suivant(t: Tournoi, tour_actuel: int) -> None:
    """Crée le tour de classement suivant (re-répartition en poules, ou tour suisse)."""
    tour_suivant = tour_actuel + 1
    if _est_suisse(t):
        from .suisse import generer_tour_suisse, suisse_termine
        if suisse_termine(t):
            raise ValueError("Le système suisse est déjà terminé.")
        generer_tour_suisse(t, tour_suivant)
        return
    if tour_suivant > t.nb_tours_brassage:
        raise ValueError("Tous les tours de brassage sont déjà créés.")
    if t.poules_tour(tour_suivant):
        return
    classement = classement_global_tour(t, tour_actuel)
    _creer_poules_brassage(t, repartir_serpentin(classement, t.nb_poules), tour=tour_suivant)
    lancer_tour_brassage(t, tour_suivant)


def brassage_termine(t: Tournoi) -> bool:
    """La phase de classement est terminée (tous les tours prévus créés et joués)."""
    if _est_suisse(t):
        from .suisse import suisse_termine
        return suisse_termine(t)
    dernier = t.nb_tours_brassage
    return bool(t.poules_tour(dernier)) and tour_brassage_termine(t, dernier)


# --------------------------------------------------------------------------- #
#  Poules finales (principale / consolante)
# --------------------------------------------------------------------------- #
def _entrelacer(a: list, b: list) -> list:
    """Entrelace deux listes (a[0], b[0], a[1], b[1], ...) pour répartir les
    poules des deux compétitions de façon alternée sur les terrains."""
    res = []
    for i in range(max(len(a), len(b))):
        if i < len(a):
            res.append(a[i])
        if i < len(b):
            res.append(b[i])
    return res


def generer_poules_finales(t: Tournoi) -> None:
    """À partir de la phase de classement, crée principale + consolante."""
    if any(p.phase in (Phase.PRINCIPALE, Phase.CONSOLANTE) for p in t.poules):
        return
    if not brassage_termine(t):
        raise ValueError("La phase de classement n'est pas terminée.")

    # Classement général unique (poules ou suisse) : moitié haute -> principale,
    # le reste -> consolante. En cas d'effectif impair, l'équipe du milieu monte
    # en principale.
    if _est_suisse(t):
        from .suisse import classement_suisse
        classees = [ligne.equipe for ligne in classement_suisse(t)]
    else:
        classees = classement_global_tour(t, t.nb_tours_brassage)
    moitie = (len(classees) + 1) // 2
    principale = classees[:moitie]
    consolante = classees[moitie:]

    nb_pf = max(1, getattr(t, "nb_poules_finales", 1))
    if principale:
        _creer_poules_groupe(t, principale, Phase.PRINCIPALE, "Principale", nb_pf)
    if consolante:
        _creer_poules_groupe(t, consolante, Phase.CONSOLANTE, "Consolante", nb_pf)

    # Une liste de matchs PAR POULE : chaque poule (principale ou consolante)
    # jouera sur son propre terrain, en parallèle des autres, pour éviter qu'une
    # même poule enchaîne tous ses matchs pendant que les autres attendent.
    groupes_p = [generer_matchs_poule(t, p) for p in t.poules_de(Phase.PRINCIPALE)]
    groupes_c = [generer_matchs_poule(t, p) for p in t.poules_de(Phase.CONSOLANTE)]
    matchs_p = [m for g in groupes_p for m in g]
    matchs_c = [m for g in groupes_c for m in g]
    # On entrelace principale et consolante pour que les deux compétitions
    # avancent ensemble même quand il y a moins de terrains que de poules.
    groupes = _entrelacer(groupes_p, groupes_c)
    ordonnancer_poules_paralleles(groupes, t.nb_terrains)
    t.matchs.extend(matchs_p)
    t.matchs.extend(matchs_c)
    # Arbitres : chaque compétition s'auto-arbitre en priorité ; si aucune équipe
    # de la compétition n'est libre, on se rabat sur l'autre compétition.
    ids_p = [e.id for e in principale]
    ids_c = [e.id for e in consolante]
    if matchs_p:
        assigner_arbitres(t, matchs_p, ids_p, ids_c)
    if matchs_c:
        assigner_arbitres(t, matchs_c, ids_c, ids_p)


def poules_finales_creees(t: Tournoi) -> bool:
    return any(p.phase in (Phase.PRINCIPALE, Phase.CONSOLANTE) for p in t.poules)


def poules_finales_terminees(t: Tournoi) -> bool:
    matchs = t.matchs_de(Phase.PRINCIPALE) + t.matchs_de(Phase.CONSOLANTE)
    return bool(matchs) and all(m.joue for m in matchs)


# --------------------------------------------------------------------------- #
#  Phase éliminatoire (un bracket par groupe)
# --------------------------------------------------------------------------- #
def generer_elimination(t: Tournoi) -> None:
    """Crée un bracket à élimination directe pour la principale et pour la
    consolante, en plaçant les équipes par tête de série (classement de la poule).
    """
    if t.matchs_de(Phase.ELIMINATION):
        return
    if not poules_finales_terminees(t):
        raise ValueError("Les poules finales ne sont pas terminées.")

    # Cible = tour de départ choisi (16 = 8e, 8 = quart, 4 = demi...), bornée au
    # nombre d'équipes réellement présentes dans le groupe : s'il y en a moins, on
    # démarre automatiquement à un tour plus avancé.
    cible_max = max(2, getattr(t, "elim_taille_tableau", 8))
    matchs: list = []
    groupes: list[list] = []
    for phase, nom in ((Phase.PRINCIPALE, "Principale"), (Phase.CONSOLANTE, "Consolante")):
        poules = t.poules_de(phase)
        if not poules:
            continue
        total = sum(len(p.equipes) for p in poules)
        cible = min(cible_max, total)
        classees = _qualifies_pour_tableau(t, poules, cible)
        bracket = generer_bracket(t, nom, classees)
        matchs += bracket
        groupes.append(bracket)

    # Principale et consolante avancent EN PARALLÈLE : les terrains sont répartis
    # entre les deux brackets au lieu de jouer tous les tours de l'un puis ceux
    # de l'autre.
    ordonnancer_elimination_parallele(groupes, t.nb_terrains)
    t.matchs.extend(matchs)
    # Arbitres des premiers tours connus (recalculés au fil des propagations).
    assigner_arbitres_elimination(t)


def elimination_creee(t: Tournoi) -> bool:
    return bool(t.matchs_de(Phase.ELIMINATION))


def elimination_terminee(t: Tournoi) -> bool:
    matchs = t.matchs_de(Phase.ELIMINATION)
    return bool(matchs) and all(m.joue for m in matchs)


def vainqueurs_finals(t: Tournoi) -> dict[str, Equipe]:
    """Vainqueur de chaque bracket (groupe -> équipe), si la finale est jouée."""
    res: dict[str, Equipe] = {}
    for m in t.matchs_de(Phase.ELIMINATION):
        if m.label_tour == "Finale" and m.vainqueur is not None:
            res[m.groupe] = m.vainqueur
    return res


def podium(t: Tournoi) -> dict[str, dict[int, Equipe]]:
    """Podium par groupe : {groupe: {1: champion, 2: finaliste, 3: 3e, 4: 4e}}.

    1/2 viennent de la finale, 3/4 de la petite finale (si elle existe).
    """
    res: dict[str, dict[int, Equipe]] = {}
    for m in t.matchs_de(Phase.ELIMINATION):
        if not m.joue:
            continue
        rangs = res.setdefault(m.groupe, {})
        if m.label_tour == "Finale":
            rangs[1] = m.vainqueur
            rangs[2] = m.perdant
        elif m.label_tour == "Petite finale":
            rangs[3] = m.vainqueur
            rangs[4] = m.perdant
    return res


# --------------------------------------------------------------------------- #
#  Classements génériques + saisie de résultats
# --------------------------------------------------------------------------- #
def classements_phase(t: Tournoi, phase: Phase) -> dict[str, list[LigneClassement]]:
    return {p.nom: classement_poule(p, t.matchs, t.regles) for p in t.poules_de(phase)}


def enregistrer_resultat(
    t: Tournoi, match_id: int,
    sets_a: int, sets_b: int,
    points_a: int | None = None, points_b: int | None = None,
) -> None:
    m = t.match_par_id(match_id)
    if m is None:
        raise KeyError(f"Match {match_id} introuvable.")
    m.sets_a, m.sets_b = sets_a, sets_b
    m.points_a, m.points_b = points_a, points_b
    if m.phase == Phase.ELIMINATION:
        propager_vainqueur(t, m)
        # De nouveaux matchs deviennent "prêts" : on (ré)affecte les arbitres.
        assigner_arbitres_elimination(t)


def enregistrer_set_sec(t: Tournoi, match_id: int, points_a: int, points_b: int) -> None:
    """Match en un set sec : le vainqueur est celui qui a le plus de points."""
    sets_a = 1 if points_a > points_b else 0
    sets_b = 1 if points_b > points_a else 0
    enregistrer_resultat(t, match_id, sets_a, sets_b, points_a, points_b)


def maj_regles(t: Tournoi, **champs) -> None:
    """Met à jour des règles de scoring à la volée (classement recalculé à
    l'affichage). N'altère pas les matchs déjà ordonnancés.
    """
    for cle, valeur in champs.items():
        if hasattr(t.regles, cle):
            setattr(t.regles, cle, valeur)


# Rétro-compat : ancien nom de l'API mono-tour.
def lancer_phase_classement(t: Tournoi) -> None:
    lancer_tour_brassage(t, 1)


def phase_classement_terminee(t: Tournoi) -> bool:
    return tour_brassage_termine(t, 1)
