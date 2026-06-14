"""Génération d'un tableau à élimination directe (bracket) avec têtes de série.

Placement classique : les têtes de série sont disposées pour que les deux
meilleures (seed 1 et seed 2) ne puissent se rencontrer qu'en finale, la 1 et la
3/4 qu'en demi-finale, etc. Les équipes manquantes (taille non puissance de 2)
deviennent des "byes" : la tête de série en face est qualifiée d'office.
"""
from __future__ import annotations

import math

from .models import Equipe, Match, Phase, Tournoi


def _puissance_deux_sup(n: int) -> int:
    p = 1
    while p < n:
        p *= 2
    return p


def ordre_tetes_de_serie(taille: int) -> list[int]:
    """Ordre des seeds (1-indexés) dans un bracket de `taille` (puissance de 2).

    Ex. taille 4 -> [1, 4, 2, 3] ; taille 8 -> [1, 8, 4, 5, 2, 7, 3, 6].
    Les paires consécutives forment les matchs du 1er tour.
    """
    res = [1]
    while len(res) < taille:
        somme = len(res) * 2 + 1
        nouveau: list[int] = []
        for s in res:
            nouveau.append(s)
            nouveau.append(somme - s)
        res = nouveau
    return res


def _label_tour(equipes_dans_le_tour: int) -> str:
    """Nomme un tour selon le nombre d'équipes encore en lice."""
    noms = {2: "Finale", 4: "Demi-finales", 8: "Quarts de finale",
            16: "8es de finale", 32: "16es de finale"}
    return noms.get(equipes_dans_le_tour, f"Tour à {equipes_dans_le_tour}")


def generer_bracket(t: Tournoi, groupe: str, classees: list[Equipe]) -> list[Match]:
    """Construit tous les matchs du bracket de `groupe` à partir des équipes
    `classees` (meilleure en premier = seed 1).

    Retourne la liste des matchs. Les matchs des tours suivants ont equipe_a /
    equipe_b à None (à déterminer) et sont reliés par next_match_id / next_slot.
    Les byes du 1er tour sont résolus immédiatement (la tête de série avance).
    """
    n = len(classees)
    if n < 2:
        return []

    taille = _puissance_deux_sup(n)
    ordre = ordre_tetes_de_serie(taille)
    # seed (1-indexé) -> équipe, ou None si bye
    seed_equipe: dict[int, Equipe | None] = {
        s: (classees[s - 1] if s <= n else None) for s in range(1, taille + 1)
    }

    matchs: list[Match] = []
    # matchs par tour, du 1er tour vers la finale
    nb_tours = int(math.log2(taille))

    # Pré-crée tous les matchs (vides) tour par tour pour pouvoir les relier.
    tours: list[list[Match]] = []
    nb_matchs = taille // 2
    for ti in range(nb_tours):
        equipes_dans_le_tour = taille // (2 ** ti)
        label = _label_tour(equipes_dans_le_tour)
        tour_matchs: list[Match] = []
        for _ in range(nb_matchs):
            tour_matchs.append(Match(
                id=t.nouveau_match_id(),
                equipe_a=None, equipe_b=None,
                poule=groupe, phase=Phase.ELIMINATION, groupe=groupe,
                tour_elim=ti + 1, label_tour=label,
            ))
        tours.append(tour_matchs)
        nb_matchs //= 2

    # Relie chaque match à son match suivant (slot a/b en alternance).
    for ti in range(nb_tours - 1):
        for idx, m in enumerate(tours[ti]):
            suivant = tours[ti + 1][idx // 2]
            m.next_match_id = suivant.id
            m.next_slot = "a" if idx % 2 == 0 else "b"

    # Petite finale (match pour la 3e place) : les deux perdants des demies.
    # Existe seulement s'il y a un tour de demi-finales (taille >= 4).
    petite_finale: Match | None = None
    if nb_tours >= 2:
        demies = tours[-2]                 # avant-dernier tour = demi-finales
        finale = tours[-1][0]
        petite_finale = Match(
            id=t.nouveau_match_id(),
            equipe_a=None, equipe_b=None,
            poule=groupe, phase=Phase.ELIMINATION, groupe=groupe,
            tour_elim=finale.tour_elim, label_tour="Petite finale",
        )
        for slot, m in zip(("a", "b"), demies):
            m.perdant_vers_id = petite_finale.id
            m.perdant_vers_slot = slot

    # Remplit le 1er tour selon l'ordre des têtes de série.
    premier = tours[0]
    for idx, m in enumerate(premier):
        sa = ordre[2 * idx]
        sb = ordre[2 * idx + 1]
        m.equipe_a = seed_equipe[sa]
        m.equipe_b = seed_equipe[sb]

    # Résout les byes du 1er tour : si un seul côté est présent, il avance.
    for m in premier:
        a, b = m.equipe_a, m.equipe_b
        if (a is None) ^ (b is None):
            gagnant = a if a is not None else b
            _propager(tours, m, gagnant)
            # le match "bye" n'a pas lieu : on le marque résolu (set 1-0 fictif ?)
            # On le retire plutôt de la liste finale.
            m._bye = True  # type: ignore[attr-defined]

    for tour_matchs in tours:
        for m in tour_matchs:
            if not getattr(m, "_bye", False):
                matchs.append(m)
    if petite_finale is not None:
        matchs.append(petite_finale)
    return matchs


def _propager(tours: list[list[Match]], match: Match, equipe) -> None:
    """Place `equipe` dans le slot du match suivant de `match`."""
    if match.next_match_id is None:
        return
    for tour_matchs in tours:
        for m in tour_matchs:
            if m.id == match.next_match_id:
                if match.next_slot == "a":
                    m.equipe_a = equipe
                else:
                    m.equipe_b = equipe
                return


def _placer(t: Tournoi, match_id: int | None, slot: str | None, equipe) -> None:
    if match_id is None or equipe is None:
        return
    cible = t.match_par_id(match_id)
    if cible is None:
        return
    if slot == "a":
        cible.equipe_a = equipe
    else:
        cible.equipe_b = equipe


def propager_vainqueur(t: Tournoi, match: Match) -> None:
    """Après saisie d'un résultat d'élimination, fait avancer le vainqueur (vers le
    tour suivant) et le perdant (vers la petite finale, si elle existe)."""
    if match.vainqueur is None:
        return
    _placer(t, match.next_match_id, match.next_slot, match.vainqueur)
    _placer(t, match.perdant_vers_id, match.perdant_vers_slot, match.perdant)
