"""Moteur du gestionnaire de tournoi de volley (sans interface)."""
from .bracket import generer_bracket, ordre_tetes_de_serie, propager_vainqueur
from .models import (
    Equipe, Match, Phase, Poule, ReglesScore, Tournoi, creer_equipes,
)
from .ranking import LigneClassement, classement_poule
from .suisse import (
    bye_du_tour, classement_suisse, nb_tours_recommande, peut_generer_tour_suivant,
    suisse_termine, tour_suisse_termine, tours_suisse,
)
from .scheduler import (
    assigner_arbitres, assigner_arbitres_elimination, generer_matchs_phase,
    generer_matchs_poule, generer_matchs_poules, ordonnancer,
    ordonnancer_elimination, ordonnancer_parallele,
)
from .persistence import dumps, from_dict, loads, to_dict
from .stats import statistiques
from .service import (
    brassage_termine, classement_global_tour, classements_phase, classements_tour,
    creer_tournoi, elimination_creee, elimination_terminee, enregistrer_resultat,
    enregistrer_set_sec, generer_elimination, generer_poules_finales,
    generer_tour_brassage_suivant, lancer_phase_classement, lancer_tour_brassage,
    maj_regles, nb_poules_pour_taille, phase_classement_terminee, podium,
    poules_finales_creees, poules_finales_terminees, repartir_serpentin,
    tailles_poules, tour_brassage_termine, vainqueurs_finals,
)

__all__ = [
    # modèles
    "Equipe", "Match", "Phase", "Poule", "ReglesScore", "Tournoi", "creer_equipes",
    # classement
    "LigneClassement", "classement_poule",
    # système suisse
    "bye_du_tour", "classement_suisse", "nb_tours_recommande",
    "peut_generer_tour_suivant", "suisse_termine", "tour_suisse_termine", "tours_suisse",
    # scheduler
    "assigner_arbitres", "assigner_arbitres_elimination",
    "generer_matchs_phase", "generer_matchs_poule", "generer_matchs_poules",
    "ordonnancer", "ordonnancer_elimination", "ordonnancer_parallele",
    # bracket
    "generer_bracket", "ordre_tetes_de_serie", "propager_vainqueur",
    # service
    "brassage_termine", "classement_global_tour", "classements_phase",
    "classements_tour", "creer_tournoi", "elimination_creee", "elimination_terminee",
    "enregistrer_resultat", "enregistrer_set_sec", "generer_elimination",
    "generer_poules_finales", "generer_tour_brassage_suivant",
    "lancer_phase_classement", "lancer_tour_brassage", "maj_regles",
    "nb_poules_pour_taille", "podium", "phase_classement_terminee",
    "poules_finales_creees", "poules_finales_terminees", "repartir_serpentin",
    "tailles_poules", "tour_brassage_termine", "vainqueurs_finals",
    # persistence
    "dumps", "loads", "to_dict", "from_dict",
    # statistiques
    "statistiques",
]
