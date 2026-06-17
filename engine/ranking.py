"""Calcul des classements de poule, paramétrable via ReglesScore."""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import cmp_to_key

from .models import Equipe, Match, Poule, ReglesScore


@dataclass
class LigneClassement:
    equipe: Equipe
    joues: int = 0
    victoires: int = 0
    defaites: int = 0
    nuls: int = 0
    points: int = 0           # points de classement
    sets_pour: int = 0
    sets_contre: int = 0
    points_pour: int = 0      # points de jeu marqués
    points_contre: int = 0

    @property
    def ratio_sets(self) -> int:
        return self.sets_pour - self.sets_contre

    @property
    def ratio_points(self) -> int:
        return self.points_pour - self.points_contre


def _accumuler(lignes: dict[int, LigneClassement], match: Match, regles: ReglesScore) -> None:
    if not match.joue:
        return
    la = lignes[match.equipe_a.id]
    lb = lignes[match.equipe_b.id]

    la.joues += 1
    lb.joues += 1
    la.sets_pour += match.sets_a
    la.sets_contre += match.sets_b
    lb.sets_pour += match.sets_b
    lb.sets_contre += match.sets_a

    if match.points_a is not None and match.points_b is not None:
        la.points_pour += match.points_a
        la.points_contre += match.points_b
        lb.points_pour += match.points_b
        lb.points_contre += match.points_a

    if match.sets_a > match.sets_b:
        la.victoires += 1
        lb.defaites += 1
        la.points += regles.points_victoire
        lb.points += regles.points_defaite
    elif match.sets_b > match.sets_a:
        lb.victoires += 1
        la.defaites += 1
        lb.points += regles.points_victoire
        la.points += regles.points_defaite
    else:
        la.nuls += 1
        lb.nuls += 1
        la.points += regles.points_nul
        lb.points += regles.points_nul


def _confrontation_directe(a: Equipe, b: Equipe, matchs: list[Match]) -> int:
    """+1 si a a gagné la confrontation directe, -1 si b, 0 sinon."""
    bilan = 0
    for m in matchs:
        if not m.joue:
            continue
        if m.implique(a) and m.implique(b):
            v = m.vainqueur
            if v is None:
                continue
            bilan += 1 if v.id == a.id else -1
    return bilan


def _trier_lignes(lignes: list[LigneClassement], matchs: list[Match],
                  regles: ReglesScore) -> list[LigneClassement]:
    """Trie des lignes déjà calculées selon l'ordre de départage des règles."""
    def comparer(x: LigneClassement, y: LigneClassement) -> int:
        for critere in regles.departage:
            if critere == "points":
                d = y.points - x.points
            elif critere == "ratio_sets":
                d = y.ratio_sets - x.ratio_sets
            elif critere == "ratio_points":
                d = y.ratio_points - x.ratio_points
            elif critere == "confrontation":
                d = -_confrontation_directe(x.equipe, y.equipe, matchs)
            else:
                d = 0
            if d != 0:
                return d
        # dernier recours : ordre stable par nom
        return (x.equipe.nom > y.equipe.nom) - (x.equipe.nom < y.equipe.nom)

    return sorted(lignes, key=cmp_to_key(comparer))


def classement_equipes(equipes: list[Equipe], matchs: list[Match],
                       regles: ReglesScore) -> list[LigneClassement]:
    """Classement d'un ensemble d'équipes sur les matchs qui les opposent.

    Pratique pour un classement *unifié* couvrant plusieurs poules d'une même
    compétition (les confrontations entre équipes de poules différentes n'existent
    pas, donc ne comptent pas). Meilleure équipe en premier.
    """
    lignes: dict[int, LigneClassement] = {e.id: LigneClassement(equipe=e) for e in equipes}
    pertinents = [
        m for m in matchs
        if m.joue and m.equipe_a is not None and m.equipe_b is not None
        and m.equipe_a.id in lignes and m.equipe_b.id in lignes
    ]
    for m in pertinents:
        _accumuler(lignes, m, regles)
    return _trier_lignes(list(lignes.values()), pertinents, regles)


def classement_poule(poule: Poule, matchs: list[Match], regles: ReglesScore) -> list[LigneClassement]:
    """Retourne les lignes de classement triées (meilleure équipe en premier)."""
    # On filtre par phase ET par nom de poule : un bracket d'élimination peut
    # porter le même nom ("Principale") que la poule, sans être le même match.
    matchs_poule = [
        m for m in matchs
        if m.poule == poule.nom and m.phase == poule.phase
    ]
    return classement_equipes(poule.equipes, matchs_poule, regles)
