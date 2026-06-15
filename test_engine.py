"""Tests rapides du moteur (sans framework, lançables avec `python test_engine.py`)."""
from collections import defaultdict

from engine import (
    Phase, ReglesScore, brassage_termine, bye_du_tour, classement_suisse,
    classements_tour, creer_tournoi, dumps, elimination_terminee,
    enregistrer_set_sec, generer_bracket, generer_elimination,
    generer_poules_finales, generer_tour_brassage_suivant, lancer_tour_brassage,
    loads, ordonnancer_parallele, ordre_tetes_de_serie, podium,
    poules_finales_terminees, suisse_termine, tour_brassage_termine,
    tours_suisse, vainqueurs_finals,
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


def jouer_suisse(t):
    """Lance et joue tous les tours d'un tournoi en système suisse."""
    lancer_tour_brassage(t, 1)
    for _ in range(50):
        n = max(tours_suisse(t))
        jouer_matchs(t, t.matchs_tour(n))
        if suisse_termine(t):
            break
        generer_tour_brassage_suivant(t, n)


def jouer_bracket(t):
    """Joue un bracket jusqu'au bout (les matchs deviennent prêts au fur et à mesure)."""
    for _ in range(50):
        prets = [m for m in t.matchs_de(Phase.ELIMINATION) if m.pret and not m.joue]
        if not prets:
            break
        jouer_matchs(t, prets)


def verifier_arbitres(matchs, pool_ids=None):
    """Vérifie qu'aucun arbitre ne joue dans sa vague et appartient au vivier.
    Retourne la charge d'arbitrage par équipe (id -> nb de matchs arbitrés).
    """
    par_vague = defaultdict(list)
    for m in matchs:
        par_vague[m.vague].append(m)
    charge = defaultdict(int)
    for vague, ms in par_vague.items():
        joueurs = set()
        for m in ms:
            for e in (m.equipe_a, m.equipe_b):
                if e is not None:
                    joueurs.add(e.id)
        arbitres_vague = []
        for m in ms:
            arb = getattr(m, "arbitre", None)
            if arb is None:
                continue
            assert arb.id not in joueurs, \
                f"vague {vague}: arbitre {arb.nom} joue aussi"
            if pool_ids is not None:
                assert arb.id in pool_ids, \
                    f"vague {vague}: arbitre {arb.nom} hors compétition"
            arbitres_vague.append(arb.id)
            charge[arb.id] += 1
        assert len(arbitres_vague) == len(set(arbitres_vague)), \
            f"vague {vague}: un arbitre est affecté à 2 matchs"
    return charge


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


def _verifier_suisse_sans_rematch(t):
    """Aucune affiche rejouée, et aucune équipe ne joue 2x dans un même tour."""
    paires = set()
    for m in t.matchs:
        if m.phase == Phase.BRASSAGE:
            cle = frozenset((m.equipe_a.id, m.equipe_b.id))
            assert cle not in paires, "affiche rejouée en système suisse"
            paires.add(cle)
    for n in tours_suisse(t):
        ids = [e.id for mm in t.matchs_tour(n) for e in (mm.equipe_a, mm.equipe_b)]
        assert len(ids) == len(set(ids)), f"tour {n}: une équipe joue 2x"


def test_suisse_illimite():
    # 8 équipes, nb de tours illimité : on s'arrête quand 1 seule équipe est invaincue.
    noms = [f"E{i}" for i in range(1, 9)]
    t = creer_tournoi("Suisse", noms, nb_poules=1, nb_terrains=2,
                      systeme="suisse", suisse_nb_tours=0)
    jouer_suisse(t)
    assert suisse_termine(t)
    _verifier_suisse_sans_rematch(t)
    cl = classement_suisse(t)
    invaincus = [l for l in cl if l.joues > 0 and l.defaites == 0]
    assert len(invaincus) == 1, f"il doit rester 1 invaincu, pas {len(invaincus)}"
    assert cl[0].equipe.nom == "E1", "E1 (gagne toujours) doit finir 1er"
    # 8 équipes -> log2(8) = 3 tours suffisent
    assert len(tours_suisse(t)) == 3, tours_suisse(t)
    print(f"  [suisse] 8 équipes, {len(tours_suisse(t))} tours -> 1 invaincu (E1)  OK")


def test_suisse_impair_bye():
    # 7 équipes : à chaque tour une équipe est exemptée (bye), sans répétition.
    noms = [f"E{i}" for i in range(1, 8)]
    t = creer_tournoi("SuisseImpair", noms, nb_poules=1, nb_terrains=2,
                      systeme="suisse", suisse_nb_tours=3)
    jouer_suisse(t)
    assert suisse_termine(t)
    _verifier_suisse_sans_rematch(t)
    byes = [bye_du_tour(t, n) for n in tours_suisse(t)]
    assert all(b is not None for b in byes), "un tour sans bye alors que nb impair"
    ids = [b.id for b in byes]
    assert len(ids) == len(set(ids)), "une équipe exemptée deux fois"
    print(f"  [suisse] 7 équipes, byes distincts {sorted(ids)}  OK")


def test_suisse_flux_complet():
    # Suisse -> principale/consolante (moitié/moitié) -> élimination.
    noms = [f"E{i}" for i in range(1, 9)]
    t = creer_tournoi("SuisseFlux", noms, nb_poules=1, nb_terrains=2,
                      systeme="suisse", suisse_nb_tours=3)
    jouer_suisse(t)
    assert brassage_termine(t)

    generer_poules_finales(t)
    principale = t.poules_de(Phase.PRINCIPALE)[0]
    consolante = t.poules_de(Phase.CONSOLANTE)[0]
    assert len(principale.equipes) == 4 and len(consolante.equipes) == 4
    # la moitié haute du classement suisse va en principale
    top4 = {l.equipe.id for l in classement_suisse(t)[:4]}
    assert {e.id for e in principale.equipes} == top4

    jouer_matchs(t, t.matchs_de(Phase.PRINCIPALE) + t.matchs_de(Phase.CONSOLANTE))
    generer_elimination(t)
    jouer_bracket(t)
    champions = vainqueurs_finals(t)
    assert "Principale" in champions and "Consolante" in champions

    # aller-retour JSON fidèle (y compris systeme/byes)
    t2 = loads(dumps(t))
    assert t2.systeme == "suisse" and t2.suisse_nb_tours == 3
    assert dumps(t2) == dumps(t), "sérialisation suisse non stable"
    print(f"  [suisse] flux complet, champion principale="
          f"{champions['Principale'].nom}  OK")


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


def test_arbitres_brassage():
    """En brassage, chaque match a un arbitre qui ne joue pas, réparti équitablement."""
    noms = [f"E{i}" for i in range(1, 9)]
    t = creer_tournoi("Arb", noms, nb_poules=2, nb_terrains=2)
    lancer_tour_brassage(t, 1)
    matchs = t.matchs_tour(1)
    # Avec 2 terrains et 8 équipes, 4 équipes se reposent par vague -> arbitre dispo.
    assert all(getattr(m, "arbitre", None) is not None for m in matchs), \
        "des matchs n'ont pas d'arbitre"
    charge = verifier_arbitres(matchs)
    ecart = max(charge.values()) - min(charge.values())
    assert ecart <= 1, f"répartition des arbitres déséquilibrée: {dict(charge)}"
    print(f"  [arbitres] brassage : tous arbitrés, écart de charge {ecart}  OK")


def test_finales_paralleles():
    """Principale et consolante se jouent en parallèle sur des terrains dédiés,
    et chaque compétition s'auto-arbitre (arbitre de la même poule)."""
    noms = [f"E{i}" for i in range(1, 9)]
    t = creer_tournoi("Para", noms, nb_poules=2, nb_terrains=4,
                      qualifies_principale_par_poule=2)
    lancer_tour_brassage(t, 1)
    jouer_matchs(t, t.matchs_tour(1))
    generer_poules_finales(t)

    mp = t.matchs_de(Phase.PRINCIPALE)
    mc = t.matchs_de(Phase.CONSOLANTE)
    ids_p = {e.id for e in t.poules_de(Phase.PRINCIPALE)[0].equipes}
    ids_c = {e.id for e in t.poules_de(Phase.CONSOLANTE)[0].equipes}

    # Terrains dédiés : avec 4 terrains, principale 1-2, consolante 3-4 (jamais de chevauchement).
    par_vague_p = defaultdict(set)
    par_vague_c = defaultdict(set)
    for m in mp:
        par_vague_p[m.vague].add(m.terrain)
    for m in mc:
        par_vague_c[m.vague].add(m.terrain)
    for v in set(par_vague_p) | set(par_vague_c):
        assert not (par_vague_p[v] & par_vague_c[v]), \
            f"vague {v}: terrains partagés entre principale et consolante"

    # Arbitres issus de la même compétition.
    verifier_arbitres(mp, ids_p)
    verifier_arbitres(mc, ids_c)
    print("  [parallèle] finales principale/consolante sur terrains dédiés + "
          "arbitres internes  OK")


def test_repartition_par_taille():
    """Déduction du nb de poules à partir d'une taille visée, toujours équilibrée."""
    from engine import nb_poules_pour_taille, tailles_poules
    # multiple exact
    assert nb_poules_pour_taille(12, 4) == 3
    assert tailles_poules(12, 3) == [4, 4, 4]
    # non-multiples -> poules équilibrées à 1 près (pas de poule isolée)
    assert nb_poules_pour_taille(10, 4) == 3
    assert tailles_poules(10, 3) == [4, 3, 3]
    assert nb_poules_pour_taille(9, 4) == 2
    assert tailles_poules(9, 2) == [5, 4]
    assert nb_poules_pour_taille(11, 4) == 3
    assert tailles_poules(11, 3) == [4, 4, 3]
    # garde-fou : jamais de poule à 1 équipe
    assert nb_poules_pour_taille(5, 2) == 2
    assert tailles_poules(5, 2) == [3, 2]
    # taille demandée >= nb d'équipes -> une seule poule
    assert nb_poules_pour_taille(4, 8) == 1

    # création réelle : les poules effectives sont équilibrées (écart <= 1)
    noms = [f"E{i}" for i in range(1, 11)]  # 10 équipes, 4 par poule
    k = nb_poules_pour_taille(len(noms), 4)
    t = creer_tournoi("Rep", noms, nb_poules=k, nb_terrains=2)
    tailles = sorted(len(p.equipes) for p in t.poules_de(Phase.BRASSAGE))
    assert tailles == [3, 3, 4], tailles
    assert max(tailles) - min(tailles) <= 1
    print(f"  [poules] répartition par taille : 10 équipes/4 -> {k} poules {tailles}  OK")


def test_arbitres_elimination():
    """En élimination, l'arbitre vient toujours de la même compétition, et de
    nouveaux arbitres apparaissent au fur et à mesure que le bracket se remplit."""
    noms = [f"E{i}" for i in range(1, 9)]
    t = creer_tournoi("Elim", noms, nb_poules=2, nb_terrains=2,
                      qualifies_principale_par_poule=2)
    lancer_tour_brassage(t, 1)
    jouer_matchs(t, t.matchs_tour(1))
    generer_poules_finales(t)
    jouer_matchs(t, t.matchs_de(Phase.PRINCIPALE) + t.matchs_de(Phase.CONSOLANTE))
    generer_elimination(t)

    ids_par_groupe = {
        p.nom: {e.id for e in p.equipes}
        for p in t.poules_de(Phase.PRINCIPALE) + t.poules_de(Phase.CONSOLANTE)
    }
    # On joue le bracket jusqu'au bout en revérifiant les arbitres à chaque étape.
    for _ in range(50):
        prets = [m for m in t.matchs_de(Phase.ELIMINATION) if m.pret and not m.joue]
        if not prets:
            break
        for m in t.matchs_de(Phase.ELIMINATION):
            arb = getattr(m, "arbitre", None)
            if arb is not None:
                assert arb.id in ids_par_groupe[m.groupe], \
                    f"{m.label_tour} {m.groupe}: arbitre hors compétition"
                assert arb.id not in (m.equipe_a.id, m.equipe_b.id), \
                    "l'arbitre joue le match"
        jouer_matchs(t, prets)
    assert elimination_terminee(t)
    print("  [arbitres] élimination : arbitres internes recalculés au fil du bracket  OK")


def test_statistiques():
    """Bilan chiffré cohérent sur un tournoi complet (poules -> finales -> élim)."""
    from engine import statistiques
    from printview import feuille_stats_html
    noms = ["A", "B", "C", "D", "E", "F", "G", "H"]
    t = creer_tournoi("Bilan", noms, nb_poules=2, nb_terrains=2, nb_tours_brassage=2)
    lancer_tour_brassage(t, 1)
    jouer_matchs(t, t.matchs_tour(1))
    generer_tour_brassage_suivant(t, 1)
    jouer_matchs(t, t.matchs_tour(2))
    generer_poules_finales(t)
    jouer_matchs(t, t.matchs_de(Phase.PRINCIPALE) + t.matchs_de(Phase.CONSOLANTE))
    generer_elimination(t)
    jouer_bracket(t)

    s = statistiques(t)
    joues = [m for m in t.matchs if m.joue]
    assert s["nb_equipes"] == 8
    assert s["matchs_joues"] == len(joues) > 0
    # somme des matchs par équipe = 2x le nombre de matchs joués
    assert sum(d["joues"] for d in s["equipes"]) == 2 * s["matchs_joues"]
    # points total = somme des points des deux équipes sur tous les matchs joués
    attendu = sum((m.points_a or 0) + (m.points_b or 0) for m in joues)
    assert s["points_total"] == attendu
    assert sum(d["points_pour"] for d in s["equipes"]) == attendu
    # arbitrages : autant d'arbitrages que de matchs (joués) ayant un arbitre
    nb_arb = sum(1 for m in t.matchs if getattr(m, "arbitre", None) is not None)
    assert sum(d["arbitrages"] for d in s["equipes"]) == nb_arb
    # podium présent pour les deux compétitions
    assert "Principale" in s["podium"] and "Consolante" in s["podium"]
    # le rendu HTML ne plante pas et contient le nom du tournoi
    html = feuille_stats_html(s)
    assert "Bilan" in html and "Classement des équipes" in html
    print(f"  [stats] {s['matchs_joues']} matchs, {s['points_total']} points, "
          f"{s['nb_equipes']} équipes  OK")


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
    test_suisse_illimite()
    test_suisse_impair_bye()
    test_suisse_flux_complet()
    test_flux_complet()
    test_arbitres_brassage()
    test_finales_paralleles()
    test_repartition_par_taille()
    test_arbitres_elimination()
    test_statistiques()
    print("Tout est vert.")
