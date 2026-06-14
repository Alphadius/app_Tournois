"""Tests rapides du moteur (sans framework, lançables avec `python test_engine.py`)."""
from collections import defaultdict

from engine import (
    Phase, ReglesScore, brassage_termine, classements_tour, creer_tournoi,
    dumps, elimination_terminee, enregistrer_set_sec, generer_bracket,
    generer_elimination, generer_poules_finales, generer_tour_brassage_suivant,
    lancer_tour_brassage, loads, ordre_tetes_de_serie, podium,
    poules_finales_terminees, tour_brassage_termine, vainqueurs_finals,
)
from engine.ranking import classement_poule


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #
def jouer_matchs(t, matchs):
    """Joue une liste de matchs : la plus petite id d'équipe gagne 25-10."""
    for m in matchs:
        if not m.pret or m.joue:
            continue
        if m.equipe_a.id < m.equipe_b.id:
            enregistrer_set_sec(t, m.id, 25, 10)
        else:
            enregistrer_set_sec(t, m.id, 10, 25)


def jouer_bracket(t):
    """Joue un bracket jusqu'au bout (les matchs deviennent prêts au fur et à mesure)."""
    for _ in range(50):
        prets = [m for m in t.matchs_de(Phase.ELIMINATION) if m.pret and not m.joue]
        if not prets:
            break
        jouer_matchs(t, prets)


def verifier_vagues(matchs, nb_terrains):
    par_vague = defaultdict(list)
    for m in matchs:
        assert m.vague is not None and m.terrain is not None, "match non ordonnancé"
        par_vague[m.vague].append(m)
    for vague, ms in par_vague.items():
        assert len(ms) <= nb_terrains, f"vague {vague}: {len(ms)} > {nb_terrains}"
        terrains = [m.terrain for m in ms]
        assert len(terrains) == len(set(terrains)), f"vague {vague}: terrain en double"
        equipes = []
        for m in ms:
            equipes += [m.equipe_a.id, m.equipe_b.id]
        assert len(equipes) == len(set(equipes)), f"vague {vague}: équipe joue 2x"
    return len(par_vague)


# --------------------------------------------------------------------------- #
#  Tests
# --------------------------------------------------------------------------- #
def test_scheduler_parallele():
    noms = [f"Equipe {i}" for i in range(1, 9)]
    t = creer_tournoi("Test", noms, nb_poules=2, nb_terrains=3)
    lancer_tour_brassage(t, 1)
    matchs = t.matchs_tour(1)
    assert len(matchs) == 12, len(matchs)
    nb = verifier_vagues(matchs, 3)
    print(f"  [parallele] 12 matchs, {nb} vagues / 3 terrains  OK")


def test_brassage_multi_tours():
    noms = [f"E{i}" for i in range(1, 9)]
    t = creer_tournoi("Brassage", noms, nb_poules=2, nb_terrains=2, nb_tours_brassage=2)

    lancer_tour_brassage(t, 1)
    jouer_matchs(t, t.matchs_tour(1))
    assert tour_brassage_termine(t, 1)
    assert not brassage_termine(t), "il reste un tour"

    # poules du tour 1
    poules_t1 = {p.nom: {e.id for e in p.equipes} for p in t.poules_tour(1)}

    generer_tour_brassage_suivant(t, 1)
    assert t.poules_tour(2), "tour 2 non créé"
    poules_t2 = {p.nom: {e.id for e in p.equipes} for p in t.poules_tour(2)}
    # la re-répartition doit changer la composition d'au moins une poule
    assert list(poules_t1.values()) != list(poules_t2.values()), "re-répartition inerte"

    jouer_matchs(t, t.matchs_tour(2))
    assert brassage_termine(t)
    print("  [brassage] 2 tours, re-répartition selon le classement  OK")


def test_seeding_bracket():
    assert ordre_tetes_de_serie(2) == [1, 2]
    assert ordre_tetes_de_serie(4) == [1, 4, 2, 3]
    assert ordre_tetes_de_serie(8) == [1, 8, 4, 5, 2, 7, 3, 6]

    # 8 équipes : seed 1 (id=1) et seed 2 (id=2) ne se croisent qu'en finale.
    t = creer_tournoi("Brk", [f"S{i}" for i in range(1, 9)], nb_poules=1, nb_terrains=2)
    equipes = list(t.equipes)  # déjà ordonnées par id = seed
    matchs = generer_bracket(t, "Principale", equipes)
    t.matchs.extend(matchs)

    premier = sorted([m for m in matchs if m.tour_elim == 1],
                     key=lambda m: (m.equipe_a.id))
    paires = {(m.equipe_a.id, m.equipe_b.id) for m in premier}
    assert paires == {(1, 8), (4, 5), (2, 7), (3, 6)}, paires

    jouer_bracket(t)
    finale = [m for m in matchs if m.label_tour == "Finale"][0]
    assert {finale.equipe_a.id, finale.equipe_b.id} == {1, 2}, "1 et 2 pas en finale"
    assert finale.vainqueur.id == 1
    print("  [bracket] têtes de série OK, finale = seed1 vs seed2  OK")


def test_bracket_avec_bye():
    # 5 équipes -> bracket de 8 -> 3 byes (seeds 6,7,8). Le tableau doit se terminer.
    t = creer_tournoi("Bye", [f"S{i}" for i in range(1, 6)], nb_poules=1, nb_terrains=2)
    matchs = generer_bracket(t, "Principale", list(t.equipes))
    t.matchs.extend(matchs)
    jouer_bracket(t)
    finale = [m for m in matchs if m.label_tour == "Finale"][0]
    assert finale.joue, "finale non jouée (bye mal géré)"
    assert finale.vainqueur.id == 1
    print(f"  [bye] 5 équipes, {len(matchs)} matchs réels, champion = seed1  OK")


def test_petite_finale():
    # 8 équipes : la petite finale oppose les deux perdants des demi-finales.
    t = creer_tournoi("PF", [f"S{i}" for i in range(1, 9)], nb_poules=1, nb_terrains=2)
    matchs = generer_bracket(t, "Principale", list(t.equipes))
    t.matchs.extend(matchs)
    pf = [m for m in matchs if m.label_tour == "Petite finale"]
    assert len(pf) == 1, "petite finale absente"
    jouer_bracket(t)
    p = podium(t)["Principale"]
    assert set(p) == {1, 2, 3, 4}, p
    # seeds plus forts (id plus petit) gagnent -> podium 1,2,3,4 dans l'ordre
    assert p[1].id == 1 and p[2].id == 2 and p[3].id < p[4].id
    print(f"  [petite finale] podium 1..4 = "
          f"{[p[r].nom for r in (1, 2, 3, 4)]}  OK")


def test_pas_de_petite_finale_a_deux():
    # 2 équipes : finale seule, pas de petite finale.
    t = creer_tournoi("PF2", ["A", "B"], nb_poules=1, nb_terrains=1)
    matchs = generer_bracket(t, "Principale", list(t.equipes))
    assert not any(m.label_tour == "Petite finale" for m in matchs)
    print("  [petite finale] absente quand 2 équipes  OK")


def test_repartition_equilibree():
    # Avec assez de matchs, aucune équipe ne doit attendre trop longtemps.
    noms = [f"E{i}" for i in range(1, 13)]  # 12 équipes
    t = creer_tournoi("Repart", noms, nb_poules=1, nb_terrains=3)
    lancer_tour_brassage(t, 1)
    matchs = t.matchs_tour(1)
    verifier_vagues(matchs, 3)
    # Pour chaque équipe, mesurer le plus grand "trou" entre deux de ses matchs.
    vagues_par_equipe = defaultdict(list)
    for m in matchs:
        for e in (m.equipe_a.id, m.equipe_b.id):
            vagues_par_equipe[e].append(m.vague)
    pire_trou = 0
    for vagues in vagues_par_equipe.values():
        vagues.sort()
        trous = [b - a for a, b in zip(vagues, vagues[1:])]
        pire_trou = max([pire_trou] + trous)
    # 12 équipes / 3 terrains : au mieux 2 équipes au repos par vague, donc un
    # petit trou est inévitable, mais il doit rester borné (<= 3 ici).
    assert pire_trou <= 3, f"trou d'attente trop grand : {pire_trou}"
    print(f"  [répartition] pire attente entre 2 matchs = {pire_trou} vague(s)  OK")


def test_json_roundtrip():
    noms = ["A", "B", "C", "D", "E", "F", "G", "H"]
    t = creer_tournoi("JSON", noms, nb_poules=2, nb_terrains=2, nb_tours_brassage=2,
                      qualifies_principale_par_poule=2)
    lancer_tour_brassage(t, 1)
    jouer_matchs(t, t.matchs_tour(1))
    generer_tour_brassage_suivant(t, 1)
    jouer_matchs(t, t.matchs_tour(2))
    generer_poules_finales(t)
    jouer_matchs(t, t.matchs_de(Phase.PRINCIPALE) + t.matchs_de(Phase.CONSOLANTE))
    generer_elimination(t)
    jouer_bracket(t)

    texte = dumps(t)
    t2 = loads(texte)
    assert t2.nom == t.nom and t2.nb_terrains == t.nb_terrains
    assert len(t2.matchs) == len(t.matchs)
    assert len(t2.equipes) == len(t.equipes)
    # le podium doit être identique après aller-retour JSON
    assert {g: {r: e.id for r, e in d.items()} for g, d in podium(t2).items()} == \
           {g: {r: e.id for r, e in d.items()} for g, d in podium(t).items()}
    # ré-sérialiser doit redonner exactement le même texte (stabilité)
    assert dumps(t2) == texte, "sérialisation non stable"
    print("  [json] sauvegarde/chargement fidèle (podium + stabilité)  OK")


def test_flux_complet():
    noms = ["A", "B", "C", "D", "E", "F", "G", "H"]
    t = creer_tournoi("Tournoi", noms, nb_poules=2, nb_terrains=2,
                      nb_tours_brassage=2, regles=ReglesScore(),
                      qualifies_principale_par_poule=2)
    lancer_tour_brassage(t, 1)
    jouer_matchs(t, t.matchs_tour(1))
    generer_tour_brassage_suivant(t, 1)
    jouer_matchs(t, t.matchs_tour(2))
    assert brassage_termine(t)

    generer_poules_finales(t)
    principale = t.poules_de(Phase.PRINCIPALE)[0]
    consolante = t.poules_de(Phase.CONSOLANTE)[0]
    assert len(principale.equipes) == 4 and len(consolante.equipes) == 4

    jouer_matchs(t, t.matchs_de(Phase.PRINCIPALE) + t.matchs_de(Phase.CONSOLANTE))
    assert poules_finales_terminees(t)

    generer_elimination(t)

    # Régression : le classement de la poule "Principale" ne doit PAS ramasser
    # les matchs du bracket homonyme (même nom, phase ELIMINATION, équipes None).
    cl_principale = classement_poule(principale, t.matchs, t.regles)
    assert all(l.joues == 3 for l in cl_principale), \
        f"classement pollué par le bracket: {[l.joues for l in cl_principale]}"

    jouer_bracket(t)
    assert elimination_terminee(t)
    champions = vainqueurs_finals(t)
    assert "Principale" in champions and "Consolante" in champions
    print(f"  [flux] champion principale={champions['Principale'].nom}, "
          f"consolante={champions['Consolante'].nom}  OK")


if __name__ == "__main__":
    print("Tests moteur :")
    test_scheduler_parallele()
    test_brassage_multi_tours()
    test_seeding_bracket()
    test_bracket_avec_bye()
    test_petite_finale()
    test_pas_de_petite_finale_a_deux()
    test_repartition_equilibree()
    test_json_roundtrip()
    test_flux_complet()
    print("Tout est vert.")
