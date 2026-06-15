"""Système suisse : appariements par niveau, sans rejouer le même adversaire.

Principe (https://fr.wikipedia.org/wiki/Système_suisse) : à chaque tour, on
oppose des équipes de classement proche. On ne refait jamais une affiche déjà
jouée. Avec un nombre impair d'équipes, une équipe est exemptée à tour de rôle
(« bye ») et marque une victoire.

Le nombre de tours peut être :
  - **fixé** (`Tournoi.suisse_nb_tours > 0`) ;
  - **illimité** (`= 0`) : on enchaîne jusqu'à ce qu'une seule équipe reste
    invaincue, avec un garde-fou à N-1 tours (toutes les affiches possibles).

Contrairement aux poules de brassage, il n'y a pas d'objet `Poule` : un tour
suisse est un ensemble de matchs (phase BRASSAGE, `tour` = n° du tour). Le
classement est **cumulé sur tous les tours**.
"""
from __future__ import annotations

from functools import cmp_to_key
from math import ceil, log2

from .models import Equipe, Match, Phase, Tournoi
from .ranking import LigneClassement, _accumuler


def nb_tours_recommande(nb_equipes: int) -> int:
    """Nombre de tours pour départager un vainqueur unique (~ log2 du nb d'équipes)."""
    return max(1, ceil(log2(nb_equipes))) if nb_equipes > 1 else 1


def label_tour(tour: int) -> str:
    return f"Tour {tour}"


# --------------------------------------------------------------------------- #
#  Classement cumulé
# --------------------------------------------------------------------------- #
def classement_suisse(t: Tournoi) -> list[LigneClassement]:
    """Classement général, cumulé sur tous les tours suisses (byes inclus)."""
    lignes: dict[int, LigneClassement] = {
        e.id: LigneClassement(equipe=e) for e in t.equipes
    }
    matchs = [
        m for m in t.matchs
        if m.phase == Phase.BRASSAGE and m.equipe_a is not None and m.equipe_b is not None
    ]
    for m in matchs:
        if m.joue and m.equipe_a.id in lignes and m.equipe_b.id in lignes:
            _accumuler(lignes, m, t.regles)

    # Une exemption (bye) compte comme une victoire (sans différentiel de jeu).
    for eid in getattr(t, "suisse_byes", []):
        if eid in lignes:
            ligne = lignes[eid]
            ligne.joues += 1
            ligne.victoires += 1
            ligne.points += t.regles.points_victoire

    def comparer(x: LigneClassement, y: LigneClassement) -> int:
        for critere in t.regles.departage:
            if critere == "points":
                d = y.points - x.points
            elif critere == "ratio_sets":
                d = y.ratio_sets - x.ratio_sets
            elif critere == "ratio_points":
                d = y.ratio_points - x.ratio_points
            else:  # "confrontation" : non pertinent globalement, ignoré
                d = 0
            if d != 0:
                return d
        return (x.equipe.nom > y.equipe.nom) - (x.equipe.nom < y.equipe.nom)

    return sorted(lignes.values(), key=cmp_to_key(comparer))


# --------------------------------------------------------------------------- #
#  État des tours
# --------------------------------------------------------------------------- #
def tours_suisse(t: Tournoi) -> list[int]:
    return sorted({m.tour for m in t.matchs if m.phase == Phase.BRASSAGE and m.tour})


def tour_suisse_termine(t: Tournoi, tour: int) -> bool:
    ms = [m for m in t.matchs if m.phase == Phase.BRASSAGE and m.tour == tour]
    return bool(ms) and all(m.joue for m in ms)


def bye_du_tour(t: Tournoi, tour: int) -> Equipe | None:
    """Équipe exemptée à ce tour (celle qui n'apparaît dans aucun match du tour)."""
    ms = [m for m in t.matchs if m.phase == Phase.BRASSAGE and m.tour == tour]
    if not ms:
        return None
    joueurs = {e.id for m in ms for e in (m.equipe_a, m.equipe_b) if e is not None}
    for e in t.equipes:
        if e.id not in joueurs:
            return e
    return None


def suisse_termine(t: Tournoi) -> bool:
    """Vrai si la phase suisse est finie (dernier tour joué + condition d'arrêt)."""
    tours = tours_suisse(t)
    if not tours:
        return False
    dernier = max(tours)
    if not tour_suisse_termine(t, dernier):
        return False
    nb = len(t.equipes)
    if t.suisse_nb_tours > 0:                     # nombre de tours fixé
        return dernier >= t.suisse_nb_tours
    # nombre de tours illimité : on s'arrête dès qu'une seule équipe est invaincue
    invaincus = sum(1 for l in classement_suisse(t) if l.joues > 0 and l.defaites == 0)
    if invaincus <= 1:
        return True
    return dernier >= max(1, nb - 1)              # garde-fou : toutes affiches jouées


def peut_generer_tour_suivant(t: Tournoi) -> bool:
    tours = tours_suisse(t)
    if not tours:
        return False
    return tour_suisse_termine(t, max(tours)) and not suisse_termine(t)


# --------------------------------------------------------------------------- #
#  Appariement
# --------------------------------------------------------------------------- #
def _paires_deja_jouees(t: Tournoi) -> set[frozenset]:
    deja: set[frozenset] = set()
    for m in t.matchs:
        if m.phase == Phase.BRASSAGE and m.equipe_a is not None and m.equipe_b is not None:
            deja.add(frozenset((m.equipe_a.id, m.equipe_b.id)))
    return deja


def _backtrack(restants: list[Equipe], deja: set[frozenset]):
    """Apparie la liste ordonnée en évitant les rematches (1er avec le plus proche)."""
    if not restants:
        return []
    a = restants[0]
    for i in range(1, len(restants)):
        b = restants[i]
        if frozenset((a.id, b.id)) in deja:
            continue
        sous = _backtrack(restants[1:i] + restants[i + 1:], deja)
        if sous is not None:
            return [(a, b)] + sous
    return None


def _apparier(ordre: list[Equipe], deja: set[frozenset], byes: set[int]):
    """Retourne (paires, bye) pour un tour, à partir du classement `ordre`."""
    ordre = list(ordre)
    bye: Equipe | None = None
    if len(ordre) % 2 == 1:
        # exempte l'équipe la moins bien classée qui n'a pas encore eu de bye
        for e in reversed(ordre):
            if e.id not in byes:
                bye = e
                break
        if bye is None:
            bye = ordre[-1]
        ordre = [e for e in ordre if e.id != bye.id]

    if not deja:                       # tour 1 : pliage haut/bas de tableau
        moitie = len(ordre) // 2
        paires = [(ordre[i], ordre[i + moitie]) for i in range(moitie)]
    else:
        paires = _backtrack(ordre, deja)
        if paires is None:             # plus d'affiche inédite : on relâche
            paires = [(ordre[i], ordre[i + 1]) for i in range(0, len(ordre) - 1, 2)]
    return paires, bye


def _ordre_pour_appariement(t: Tournoi) -> list[Equipe]:
    deja_joue = any(m.phase == Phase.BRASSAGE and m.joue for m in t.matchs)
    if deja_joue or t.suisse_byes:
        return [l.equipe for l in classement_suisse(t)]
    return list(t.equipes)             # tour 1 : ordre de saisie = têtes de série


def generer_tour_suisse(t: Tournoi, tour: int) -> None:
    """Crée et ordonnance les matchs d'un tour suisse (idempotent)."""
    if any(m.phase == Phase.BRASSAGE and m.tour == tour for m in t.matchs):
        return
    from .scheduler import ordonnancer  # import local : évite un cycle d'import

    ordre = _ordre_pour_appariement(t)
    paires, bye = _apparier(ordre, _paires_deja_jouees(t), set(t.suisse_byes))

    matchs = [
        Match(id=t.nouveau_match_id(), equipe_a=a, equipe_b=b,
              poule=label_tour(tour), phase=Phase.BRASSAGE, tour=tour)
        for a, b in paires
    ]
    if bye is not None:
        t.suisse_byes.append(bye.id)
    ordonnancer(matchs, t.nb_terrains)
    t.matchs.extend(matchs)
