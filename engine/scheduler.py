"""Génération des matchs (round-robin) et ordonnancement parallèle sur N terrains.

L'ordonnanceur répartit les matchs en *vagues* (créneaux simultanés).
Contraintes :
  - une équipe ne joue pas deux matchs dans la même vague ;
  - au plus `nb_terrains` matchs par vague.
On essaie aussi d'équilibrer le temps de repos en évitant, autant que possible,
qu'une équipe enchaîne deux vagues d'affilée.
"""
from __future__ import annotations

from itertools import combinations

from .models import Equipe, Match, Phase, Poule, Tournoi


def generer_matchs_poule(tournoi: Tournoi, poule: Poule) -> list[Match]:
    """Round-robin (toutes les paires) pour une poule, aller simple ou aller-retour."""
    matchs: list[Match] = []
    for a, b in combinations(poule.equipes, 2):
        matchs.append(Match(
            id=tournoi.nouveau_match_id(),
            equipe_a=a, equipe_b=b, poule=poule.nom, phase=poule.phase,
            tour=poule.tour,
        ))
        if tournoi.regles.aller_retour:
            matchs.append(Match(
                id=tournoi.nouveau_match_id(),
                equipe_a=b, equipe_b=a, poule=poule.nom, phase=poule.phase,
                tour=poule.tour,
            ))
    return matchs


def generer_matchs_phase(tournoi: Tournoi, phase: Phase) -> list[Match]:
    """Génère les matchs de toutes les poules d'une phase."""
    matchs: list[Match] = []
    for poule in tournoi.poules_de(phase):
        matchs.extend(generer_matchs_poule(tournoi, poule))
    return matchs


def generer_matchs_poules(tournoi: Tournoi, poules: list[Poule]) -> list[Match]:
    """Génère les matchs d'une liste de poules données (ex: un tour de brassage)."""
    matchs: list[Match] = []
    for poule in poules:
        matchs.extend(generer_matchs_poule(tournoi, poule))
    return matchs


def ordonnancer_elimination(matchs: list[Match], nb_terrains: int,
                            vague_depart: int = 1) -> int:
    """Ordonnance un bracket : chaque tour d'élimination occupe ses propres vagues
    (un tour ne peut commencer qu'une fois le précédent terminé). Dans un même
    tour, aucune équipe n'apparaît deux fois, donc on remplit simplement les
    terrains. Retourne la prochaine vague libre.
    """
    vague = vague_depart
    tours = sorted({m.tour_elim for m in matchs if m.tour_elim is not None})
    for te in tours:
        du_tour = [m for m in matchs if m.tour_elim == te]
        terrain = 1
        for m in du_tour:
            if terrain > nb_terrains:
                terrain = 1
                vague += 1
            m.vague = vague
            m.terrain = terrain
            terrain += 1
        vague += 1
    return vague


def _ordonnancer_elimination_bloc(matchs: list[Match], terrain_debut: int,
                                  nb_terrains_bloc: int,
                                  vague_depart: int = 1) -> int:
    """Ordonnance un bracket sur un bloc de terrains réservé
    (`terrain_debut`..`terrain_debut+nb_terrains_bloc-1`). Comme
    `ordonnancer_elimination`, chaque tour occupe ses propres vagues (un tour ne
    commence qu'une fois le précédent fini). Retourne la prochaine vague libre.
    """
    if nb_terrains_bloc < 1:
        raise ValueError("Bloc de terrains vide.")
    vague = vague_depart
    tours = sorted({m.tour_elim for m in matchs if m.tour_elim is not None})
    for te in tours:
        du_tour = [m for m in matchs if m.tour_elim == te]
        terrain = terrain_debut
        fin = terrain_debut + nb_terrains_bloc
        for m in du_tour:
            if terrain >= fin:
                terrain = terrain_debut
                vague += 1
            m.vague = vague
            m.terrain = terrain
            terrain += 1
        vague += 1
    return vague


def ordonnancer_elimination_parallele(groupes: list[list[Match]],
                                      nb_terrains: int,
                                      vague_depart: int = 1) -> int:
    """Ordonnance plusieurs brackets EN PARALLÈLE, chacun sur son bloc de terrains.

    `groupes` : une liste de matchs par bracket (ex : principale + consolante).
    Les terrains sont répartis entre les brackets (comme
    `ordonnancer_poules_paralleles`) afin que principale et consolante avancent
    en même temps, au lieu de jouer tous les quarts d'une compétition puis tous
    ceux de l'autre. Retourne la prochaine vague libre.
    """
    if nb_terrains < 1:
        raise ValueError("Il faut au moins 1 terrain.")
    groupes = [list(g) for g in groupes if g]
    if not groupes:
        return vague_depart

    vague_globale = vague_depart
    for debut in range(0, len(groupes), nb_terrains):
        lot = groupes[debut:debut + nb_terrains]
        n = len(lot)
        base = nb_terrains // n
        extra = nb_terrains % n
        terrain = 1
        fins = []
        for i, matchs in enumerate(lot):
            nb = base + (1 if i < extra else 0)
            fins.append(_ordonnancer_elimination_bloc(matchs, terrain, nb,
                                                      vague_globale))
            terrain += nb
        vague_globale = max(fins)
    return vague_globale


def ordonnancer(matchs: list[Match], nb_terrains: int, vague_depart: int = 1) -> int:
    """Affecte terrain + vague aux matchs (modifie les objets en place).

    Objectif : remplir les terrains à chaque vague TOUT EN évitant qu'une équipe
    reste trop longtemps sans jouer. À chaque vague on traite en priorité les
    matchs dont une équipe attend depuis le plus longtemps (max du temps d'attente
    des deux équipes), puis on complète les terrains restants avec d'autres matchs
    sans conflit d'équipe.

    Contraintes garanties : <= nb_terrains matchs par vague, et aucune équipe ne
    joue deux fois dans la même vague.

    Retourne le numéro de la prochaine vague libre (utile pour enchaîner).
    """
    if nb_terrains < 1:
        raise ValueError("Il faut au moins 1 terrain.")

    a_placer = list(matchs)
    vague = vague_depart
    # Dernière vague jouée par chaque équipe (vague_depart - 1 = pas encore joué).
    derniere_vague: dict[int, int] = {}
    base = vague_depart - 1

    def attente(team_id: int) -> int:
        return vague - derniere_vague.get(team_id, base)

    while a_placer:
        occupees: set[int] = set()
        terrain = 1

        # Priorité : l'équipe la plus en attente d'abord (max), puis la somme des
        # attentes (départage). Tri décroissant = les plus urgents en tête.
        def priorite(m: Match) -> tuple[int, int]:
            wa, wb = attente(m.equipe_a.id), attente(m.equipe_b.id)
            return (max(wa, wb), wa + wb)

        candidats = sorted(a_placer, key=priorite, reverse=True)

        restants: list[Match] = []
        for m in candidats:
            a, b = m.equipe_a.id, m.equipe_b.id
            if terrain > nb_terrains or a in occupees or b in occupees:
                restants.append(m)
                continue
            m.vague = vague
            m.terrain = terrain
            occupees.update((a, b))
            derniere_vague[a] = vague
            derniere_vague[b] = vague
            terrain += 1

        a_placer = restants
        vague += 1

    return vague


# --------------------------------------------------------------------------- #
#  Ordonnancement parallèle de deux compétitions (principale / consolante)
# --------------------------------------------------------------------------- #
def _budget_terrains(nb_terrains: int, idx_vague: int) -> tuple[int, int]:
    """Répartition des terrains entre principale et consolante pour une vague.

    Nombre pair : moitié / moitié. Nombre impair : le terrain en plus va
    alternativement à la principale (vagues paires) puis à la consolante
    (vagues impaires), pour ne favoriser aucune des deux compétitions.
    """
    moitie = nb_terrains // 2
    if nb_terrains % 2 == 0:
        return moitie, moitie
    if idx_vague % 2 == 0:
        return moitie + 1, moitie
    return moitie, moitie + 1


def _placer_vague(matchs: list[Match], budget: int, vague: int,
                  terrain_debut: int, derniere_vague: dict[int, int],
                  base: int) -> list[Match]:
    """Place jusqu'à `budget` matchs sur la vague donnée (terrains
    `terrain_debut`..`terrain_debut+budget-1`), en priorisant le repos.
    Retourne les matchs non placés.
    """
    if budget < 1:
        return list(matchs)

    def attente(team_id: int) -> int:
        return vague - derniere_vague.get(team_id, base)

    def priorite(m: Match) -> tuple[int, int]:
        wa, wb = attente(m.equipe_a.id), attente(m.equipe_b.id)
        return (max(wa, wb), wa + wb)

    occupees: set[int] = set()
    terrain = terrain_debut
    fin = terrain_debut + budget
    restants: list[Match] = []
    for m in sorted(matchs, key=priorite, reverse=True):
        a, b = m.equipe_a.id, m.equipe_b.id
        if terrain >= fin or a in occupees or b in occupees:
            restants.append(m)
            continue
        m.vague = vague
        m.terrain = terrain
        occupees.update((a, b))
        derniere_vague[a] = vague
        derniere_vague[b] = vague
        terrain += 1
    return restants


def _ordonnancer_bloc(matchs: list[Match], terrain_debut: int,
                      nb_terrains_bloc: int, vague_depart: int) -> int:
    """Ordonnance des matchs sur un bloc de terrains réservé
    (`terrain_debut`..`terrain_debut+nb_terrains_bloc-1`), en équilibrant le repos.
    Retourne la prochaine vague libre.
    """
    if nb_terrains_bloc < 1:
        raise ValueError("Bloc de terrains vide.")
    a_placer = list(matchs)
    vague = vague_depart
    base = vague_depart - 1
    derniere_vague: dict[int, int] = {}
    while a_placer:
        a_placer = _placer_vague(a_placer, nb_terrains_bloc, vague,
                                 terrain_debut, derniere_vague, base)
        vague += 1
    return vague


def ordonnancer_poules_paralleles(groupes: list[list[Match]], nb_terrains: int,
                                  vague_depart: int = 1) -> int:
    """Ordonnance plusieurs poules EN PARALLÈLE, chacune sur son/ses terrain(s).

    `groupes` : une liste de matchs par poule. Chaque poule joue son round-robin
    sur un bloc de terrains qui lui est réservé, donc les poules avancent
    simultanément (4 poules + 4 terrains = chaque poule sur un terrain, aucune
    n'attend que les autres aient fini).

    Répartition des terrains :
      - s'il y a au plus autant de poules que de terrains, chaque poule reçoit au
        moins un terrain et les terrains en surplus accélèrent les premières
        poules (qui font alors jouer 2 matchs de front) ;
      - s'il y a plus de poules que de terrains, les poules sont traitées par
        lots successifs (un lot démarre quand le précédent est terminé).

    Retourne la prochaine vague libre.
    """
    if nb_terrains < 1:
        raise ValueError("Il faut au moins 1 terrain.")
    groupes = [list(g) for g in groupes if g]
    if not groupes:
        return vague_depart

    vague_globale = vague_depart
    for debut in range(0, len(groupes), nb_terrains):
        lot = groupes[debut:debut + nb_terrains]
        n = len(lot)
        base = nb_terrains // n
        extra = nb_terrains % n
        terrain = 1
        fins = []
        for i, matchs in enumerate(lot):
            nb = base + (1 if i < extra else 0)
            fins.append(_ordonnancer_bloc(matchs, terrain, nb, vague_globale))
            terrain += nb
        vague_globale = max(fins)
    return vague_globale


def ordonnancer_parallele(matchs_p: list[Match], matchs_c: list[Match],
                          nb_terrains: int, vague_depart: int = 1) -> int:
    """Ordonnance deux compétitions EN PARALLÈLE sur des terrains dédiés.

    La principale occupe les premiers terrains, la consolante les suivants ;
    aucune ne déborde sur les terrains de l'autre (les deux tournois se jouent
    réellement côte à côte). La répartition des terrains suit `_budget_terrains`.
    Retourne la prochaine vague libre.
    """
    if nb_terrains < 1:
        raise ValueError("Il faut au moins 1 terrain.")

    a_placer_p = list(matchs_p)
    a_placer_c = list(matchs_c)
    vague = vague_depart
    base = vague_depart - 1
    derniere_vague: dict[int, int] = {}

    while a_placer_p or a_placer_c:
        idx = vague - vague_depart
        budget_p, budget_c = _budget_terrains(nb_terrains, idx)
        # Si une compétition est terminée, l'autre récupère tous les terrains.
        if not a_placer_p:
            budget_c = nb_terrains
        elif not a_placer_c:
            budget_p = nb_terrains

        a_placer_p = _placer_vague(a_placer_p, budget_p, vague, 1,
                                   derniere_vague, base)
        a_placer_c = _placer_vague(a_placer_c, budget_c, vague,
                                   budget_p + 1, derniere_vague, base)
        vague += 1

    return vague


# --------------------------------------------------------------------------- #
#  Affectation des arbitres (équipes qui ne jouent pas)
# --------------------------------------------------------------------------- #
def assigner_arbitres(t: Tournoi, matchs: list[Match],
                      pool_ids: list[int] | None = None,
                      fallback_ids: list[int] | None = None) -> None:
    """Affecte une équipe arbitre à chaque match parmi les équipes qui ne jouent
    pas pendant la vague du match, en équilibrant la charge d'arbitrage.

    - `pool_ids` : vivier d'arbitres prioritaire (ex : même compétition en
      finales / élimination). Par défaut, toutes les équipes.
    - `fallback_ids` : vivier de secours, utilisé seulement quand aucune équipe
      du vivier prioritaire n'est disponible (ex : l'autre compétition). Permet
      d'arbitrer un match consolante avec une équipe principale et inversement.
    - Si vraiment aucune équipe (ni prioritaire ni secours) n'est libre, le match
      est marqué `arbitre_auto = True` (arbitrage auto-géré).
    - La charge initiale tient compte des arbitrages déjà affectés ailleurs dans
      le tournoi (`t.matchs`), pour rester homogène d'une phase à l'autre.
    """
    par_id = {e.id: e for e in t.equipes}
    if pool_ids is None:
        pool_ids = [e.id for e in t.equipes]
    pool = [i for i in pool_ids if i in par_id]
    pool_set = set(pool)
    fallback = [i for i in (fallback_ids or [])
                if i in par_id and i not in pool_set]

    # Charge globale courante (arbitrages déjà posés sur d'autres matchs).
    univers = pool + fallback
    charge: dict[int, int] = {i: 0 for i in univers}
    cibles = {id(m) for m in matchs}
    for m in t.matchs:
        arb = getattr(m, "arbitre", None)
        if arb is not None and arb.id in charge and id(m) not in cibles:
            charge[arb.id] += 1

    # On (ré)affecte les matchs cibles, regroupés par vague.
    for m in matchs:
        m.arbitre = None
        m.arbitre_auto = False
    par_vague: dict[int, list[Match]] = {}
    for m in matchs:
        par_vague.setdefault(m.vague if m.vague is not None else -1, []).append(m)

    for vague in sorted(par_vague):
        groupe = par_vague[vague]
        joueurs: set[int] = set()
        for m in groupe:
            for e in (m.equipe_a, m.equipe_b):
                if e is not None:
                    joueurs.add(e.id)
        occupes: set[int] = set()  # arbitres déjà pris sur cette vague

        def libres(viv: list[int]) -> list[int]:
            return [i for i in viv if i not in joueurs and i not in occupes]

        for m in groupe:
            if m.equipe_a is None or m.equipe_b is None:
                continue  # slot de bracket non encore résolu
            # Vivier prioritaire d'abord, puis vivier de secours.
            candidats = libres(pool) or libres(fallback)
            if not candidats:
                m.arbitre_auto = True  # aucune équipe disponible
                continue
            choix = min(candidats, key=lambda i: (charge[i], i))
            m.arbitre = par_id[choix]
            charge[choix] += 1
            occupes.add(choix)


def assigner_arbitres_elimination(t: Tournoi) -> None:
    """Affecte les arbitres des matchs d'élimination, compétition par compétition
    (un arbitre vient toujours de la MÊME compétition que le match arbitré).

    À rappeler après chaque propagation : les matchs dont les deux équipes ne
    sont pas encore connues restent sans arbitre jusqu'à ce qu'elles le soient.
    """
    # Vivier de chaque compétition (pour le secours croisé).
    viviers: dict[Phase, list[int]] = {}
    for phase in (Phase.PRINCIPALE, Phase.CONSOLANTE):
        poules = t.poules_de(phase)
        viviers[phase] = [e.id for e in poules[0].equipes] if poules else []

    for phase in (Phase.PRINCIPALE, Phase.CONSOLANTE):
        poules = t.poules_de(phase)
        if not poules:
            continue
        pool_ids = viviers[phase]
        autre = Phase.CONSOLANTE if phase == Phase.PRINCIPALE else Phase.PRINCIPALE
        fallback_ids = viviers.get(autre, [])
        groupe = poules[0].nom
        ms = [m for m in t.matchs_de(Phase.ELIMINATION) if m.groupe == groupe]
        if ms:
            assigner_arbitres(t, ms, pool_ids, fallback_ids)
