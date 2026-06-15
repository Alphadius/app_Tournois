"""Modèles de données du tournoi de volley.

Tout est en dataclasses simples, sérialisables, sans dépendance externe.
Le moteur (models / ranking / scheduler) ne connaît pas l'interface.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from itertools import count
from typing import Optional


class Phase(str, Enum):
    """Phases d'un tournoi.

    Déroulé : un ou plusieurs tours de BRASSAGE (poules de classement, re-réparties
    selon le niveau après chaque tour) -> PRINCIPALE / CONSOLANTE (poules finales)
    -> ELIMINATION (bracket à élimination directe, un par groupe).
    """
    BRASSAGE = "brassage"          # poules de classement (un ou plusieurs tours)
    PRINCIPALE = "principale"      # poule principale (haut de tableau)
    CONSOLANTE = "consolante"      # poule consolante (bas de tableau)
    ELIMINATION = "elimination"    # tableau à élimination directe

    # Alias rétro-compatible
    CLASSEMENT = "brassage"


@dataclass
class Equipe:
    id: int
    nom: str

    def __hash__(self) -> int:
        return hash(self.id)


@dataclass
class ReglesScore:
    """Règles paramétrables de scoring et de départage.

    Format de match :
      - "set_sec"  : un seul set, on saisit les points marqués (ex 25-20),
                     le vainqueur est celui qui a le plus de points.
      - "best_of"  : au meilleur des X sets, on saisit les sets gagnés (ex 2-1).

    Le départage utilise, dans l'ordre, les critères listés dans `departage`.
    Critères disponibles :
      - "points"      : points de classement (victoires)
      - "confrontation": résultat de la confrontation directe (2 équipes)
      - "ratio_points": (points marqués - points encaissés)
      - "ratio_sets"  : (sets gagnés - sets perdus)
    """
    format_match: str = "set_sec"      # "set_sec" ou "best_of"
    points_pour_gagner: int = 25       # cible de points d'un set sec
    points_victoire: int = 3
    points_defaite: int = 0
    points_nul: int = 1                # volley = rarement de nul, mais on le garde
    aller_retour: bool = False         # round-robin simple ou aller-retour
    departage: list[str] = field(
        default_factory=lambda: ["points", "confrontation", "ratio_points", "ratio_sets"]
    )


@dataclass
class Match:
    id: int
    equipe_a: Optional[Equipe]     # None = à déterminer (slot de bracket)
    equipe_b: Optional[Equipe]
    poule: str                     # nom de la poule (ex: "Poule A")
    phase: Phase
    tour: int = 0                  # n° de tour de brassage (1..N), 0 sinon
    # résultat (None tant que non joué)
    sets_a: Optional[int] = None
    sets_b: Optional[int] = None
    points_a: Optional[int] = None  # total points marqués (optionnel)
    points_b: Optional[int] = None
    # ordonnancement
    terrain: Optional[int] = None   # n° de terrain (1..N)
    vague: Optional[int] = None     # n° de vague (créneau parallèle)
    # élimination directe (bracket)
    groupe: Optional[str] = None    # "Principale" / "Consolante"
    tour_elim: Optional[int] = None  # 1 = premier tour du bracket
    label_tour: Optional[str] = None  # "Finale", "1/2", "1/4"...
    next_match_id: Optional[int] = None  # match où va le vainqueur
    next_slot: Optional[str] = None  # 'a' ou 'b' dans le match suivant
    perdant_vers_id: Optional[int] = None  # match où va le perdant (petite finale)
    perdant_vers_slot: Optional[str] = None

    @property
    def joue(self) -> bool:
        if self.equipe_a is None or self.equipe_b is None:
            return False
        return self.sets_a is not None and self.sets_b is not None

    @property
    def pret(self) -> bool:
        """Les deux équipes sont connues (utile pour le bracket)."""
        return self.equipe_a is not None and self.equipe_b is not None

    @property
    def vainqueur(self) -> Optional[Equipe]:
        if not self.joue or self.sets_a == self.sets_b:
            return None
        return self.equipe_a if self.sets_a > self.sets_b else self.equipe_b

    @property
    def perdant(self) -> Optional[Equipe]:
        v = self.vainqueur
        if v is None:
            return None
        return self.equipe_b if v.id == self.equipe_a.id else self.equipe_a

    def implique(self, equipe: Equipe) -> bool:
        ids = {e.id for e in (self.equipe_a, self.equipe_b) if e is not None}
        return equipe.id in ids


@dataclass
class Poule:
    nom: str
    phase: Phase
    equipes: list[Equipe] = field(default_factory=list)
    tour: int = 0                  # n° de tour de brassage (1..N), 0 sinon


@dataclass
class Tournoi:
    nom: str
    nb_terrains: int
    regles: ReglesScore = field(default_factory=ReglesScore)
    equipes: list[Equipe] = field(default_factory=list)
    poules: list[Poule] = field(default_factory=list)
    matchs: list[Match] = field(default_factory=list)
    nb_poules: int = 1             # nb de poules par tour de brassage
    nb_tours_brassage: int = 1     # nb de tours de brassage
    # combien d'équipes de chaque poule de classement montent en principale
    qualifies_principale_par_poule: int = 1
    # phase de classement : "poules" (brassage en poules) ou "suisse" (système suisse)
    systeme: str = "poules"
    # système suisse : 0 = nb de tours illimité (jusqu'à une seule équipe invaincue),
    # > 0 = nombre de tours fixé
    suisse_nb_tours: int = 0
    # ids des équipes déjà exemptées (bye) en système suisse, pour ne pas répéter
    suisse_byes: list[int] = field(default_factory=list)
    _id_seq: int = field(default=0, repr=False)

    def nouveau_match_id(self) -> int:
        self._id_seq += 1
        return self._id_seq

    def poules_de(self, phase: Phase) -> list[Poule]:
        return [p for p in self.poules if p.phase == phase]

    def poules_tour(self, tour: int) -> list[Poule]:
        return [p for p in self.poules
                if p.phase == Phase.BRASSAGE and p.tour == tour]

    def matchs_de(self, phase: Phase) -> list[Match]:
        return [m for m in self.matchs if m.phase == phase]

    def matchs_tour(self, tour: int) -> list[Match]:
        return [m for m in self.matchs
                if m.phase == Phase.BRASSAGE and m.tour == tour]

    def match_par_id(self, match_id: int) -> Optional[Match]:
        for m in self.matchs:
            if m.id == match_id:
                return m
        return None


def creer_equipes(noms: list[str]) -> list[Equipe]:
    """Crée des équipes à partir d'une liste de noms."""
    c = count(1)
    return [Equipe(id=next(c), nom=nom.strip()) for nom in noms if nom.strip()]
