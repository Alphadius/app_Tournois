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
