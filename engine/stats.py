"""Statistiques récapitulatives d'un tournoi (bilan de fin de tournoi).

Tout est calculé à partir des matchs déjà joués : nombre de matchs, de points et
de sets, classement complet des équipes, faits marquants et podiums. Le module
est purement « moteur » (aucune dépendance à l'interface) pour rester testable.
"""
from __future__ import annotations

from .models import Phase, Tournoi

_LIBELLE_PHASE = {
    Phase.BRASSAGE: "Brassage / Suisse",
    Phase.PRINCIPALE: "Poule principale",
    Phase.CONSOLANTE: "Poule consolante",
    Phase.ELIMINATION: "Élimination directe",
}


def _pts(x) -> int:
    return x or 0


def _ecart(m) -> int:
    return abs(_pts(m.points_a) - _pts(m.points_b))


def _total(m) -> int:
    return _pts(m.points_a) + _pts(m.points_b)


def statistiques(t: Tournoi) -> dict:
    """Calcule le bilan chiffré du tournoi (dict prêt à afficher / exporter)."""
    matchs = t.matchs
    joues = [m for m in matchs if m.joue]

    points_total = sum(_total(m) for m in joues)
    sets_total = sum(_pts(m.sets_a) + _pts(m.sets_b) for m in joues)
    marges = [_ecart(m) for m in joues]
    vagues = {m.vague for m in matchs if m.vague is not None}

    # --- bilan par phase ---
    par_phase = []
    for ph in (Phase.BRASSAGE, Phase.PRINCIPALE, Phase.CONSOLANTE, Phase.ELIMINATION):
        ph_joues = [m for m in joues if m.phase == ph]
        if not ph_joues:
            continue
        par_phase.append({
            "phase": _LIBELLE_PHASE[ph],
            "matchs": len(ph_joues),
            "points": sum(_total(m) for m in ph_joues),
        })

    # --- bilan par équipe ---
    stats = {e.id: {
        "equipe": e, "joues": 0, "victoires": 0, "defaites": 0,
        "points_pour": 0, "points_contre": 0, "arbitrages": 0,
    } for e in t.equipes}
    for m in joues:
        a, b = m.equipe_a, m.equipe_b
        if a is None or b is None or a.id not in stats or b.id not in stats:
            continue
        pa, pb = _pts(m.points_a), _pts(m.points_b)
        stats[a.id]["joues"] += 1
        stats[b.id]["joues"] += 1
        stats[a.id]["points_pour"] += pa
        stats[a.id]["points_contre"] += pb
        stats[b.id]["points_pour"] += pb
        stats[b.id]["points_contre"] += pa
        v = m.vainqueur
        if v is not None:
            stats[v.id]["victoires"] += 1
            perd = m.perdant
            if perd is not None:
                stats[perd.id]["defaites"] += 1
    for m in matchs:
        arb = getattr(m, "arbitre", None)
        if arb is not None and arb.id in stats:
            stats[arb.id]["arbitrages"] += 1

    byes: dict[int, int] = {}
    for eid in getattr(t, "suisse_byes", []):
        byes[eid] = byes.get(eid, 0) + 1

    # Groupe final de chaque équipe (principale / consolante) d'après les poules
    # finales. Sert à classer la principale AVANT la consolante : il n'est pas
    # logique qu'une équipe de consolante devance une équipe de principale.
    groupe_par_equipe: dict[int, str] = {}
    for p in t.poules:
        if p.phase == Phase.PRINCIPALE:
            for e in p.equipes:
                groupe_par_equipe[e.id] = "Principale"
        elif p.phase == Phase.CONSOLANTE:
            for e in p.equipes:
                groupe_par_equipe[e.id] = "Consolante"
    rang_groupe = {"Principale": 0, "Consolante": 1}

    equipes = []
    for s in stats.values():
        d = dict(s)
        d["diff"] = s["points_pour"] - s["points_contre"]
        d["byes"] = byes.get(s["equipe"].id, 0)
        d["groupe"] = groupe_par_equipe.get(s["equipe"].id)
        equipes.append(d)
    # Tri : groupe (principale avant consolante avant non-classé), puis victoires,
    # différence de points, points marqués (tous décroissants).
    equipes.sort(key=lambda d: (rang_groupe.get(d["groupe"], 2),
                                -d["victoires"], -d["diff"], -d["points_pour"]))

    # --- faits marquants ---
    faits: dict = {}
    if joues:
        faits["plus_large"] = max(joues, key=_ecart)
        non_nuls = [m for m in joues if _ecart(m) > 0]
        faits["plus_serre"] = min(non_nuls, key=_ecart) if non_nuls else None
        faits["plus_prolifique"] = max(joues, key=_total)
    if equipes:
        att = max(equipes, key=lambda d: d["points_pour"])
        faits["meilleure_attaque"] = att if att["points_pour"] else None
        joueurs = [d for d in equipes if d["joues"] > 0]
        if joueurs:
            faits["meilleure_defense"] = min(
                joueurs, key=lambda d: d["points_contre"] / d["joues"])
        top_arb = max(equipes, key=lambda d: d["arbitrages"])
        faits["plus_arbitre"] = top_arb if top_arb["arbitrages"] else None

    from .service import podium
    pod = podium(t)

    return {
        "nom": t.nom,
        "systeme": getattr(t, "systeme", "poules"),
        "nb_equipes": len(t.equipes),
        "nb_terrains": t.nb_terrains,
        "nb_vagues": len(vagues),
        "matchs_joues": len(joues),
        "matchs_prets": len([m for m in matchs if m.pret]),
        "points_total": points_total,
        "sets_total": sets_total,
        "points_moyen_par_match": round(points_total / len(joues), 1) if joues else 0,
        "marge_moyenne": round(sum(marges) / len(marges), 1) if marges else 0,
        "par_phase": par_phase,
        "equipes": equipes,
        "faits": faits,
        "podium": pod,
    }
