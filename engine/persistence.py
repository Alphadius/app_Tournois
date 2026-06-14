"""Sauvegarde / chargement d'un tournoi au format JSON.

On sérialise les équipes par id et on les référence partout par id, pour éviter
de dupliquer les objets et garder un fichier lisible.
"""
from __future__ import annotations

import json
from dataclasses import asdict

from .models import Equipe, Match, Phase, Poule, ReglesScore, Tournoi

FORMAT_VERSION = 1

_MATCH_CHAMPS = (
    "id", "poule", "tour", "sets_a", "sets_b", "points_a", "points_b",
    "terrain", "vague", "groupe", "tour_elim", "label_tour",
    "next_match_id", "next_slot", "perdant_vers_id", "perdant_vers_slot",
)


def _eid(equipe: Equipe | None) -> int | None:
    return equipe.id if equipe is not None else None


def to_dict(t: Tournoi) -> dict:
    # getattr(..., défaut) : tolère un objet créé par une version antérieure du
    # code (Streamlit garde les objets en mémoire lors d'un rechargement à chaud).
    return {
        "format_version": FORMAT_VERSION,
        "nom": t.nom,
        "nb_terrains": t.nb_terrains,
        "nb_poules": getattr(t, "nb_poules", 1),
        "nb_tours_brassage": getattr(t, "nb_tours_brassage", 1),
        "qualifies_principale_par_poule": getattr(t, "qualifies_principale_par_poule", 1),
        "_id_seq": getattr(t, "_id_seq", 0),
        "regles": asdict(t.regles),
        "equipes": [{"id": e.id, "nom": e.nom} for e in t.equipes],
        "poules": [
            {"nom": p.nom, "phase": p.phase.value, "tour": getattr(p, "tour", 0),
             "equipe_ids": [e.id for e in p.equipes]}
            for p in t.poules
        ],
        "matchs": [
            {**{c: getattr(m, c, None) for c in _MATCH_CHAMPS},
             "phase": m.phase.value,
             "equipe_a_id": _eid(m.equipe_a), "equipe_b_id": _eid(m.equipe_b)}
            for m in t.matchs
        ],
    }


def from_dict(d: dict) -> Tournoi:
    equipes = [Equipe(id=e["id"], nom=e["nom"]) for e in d["equipes"]]
    par_id = {e.id: e for e in equipes}

    def eq(i):
        return par_id[i] if i is not None else None

    t = Tournoi(
        nom=d["nom"],
        nb_terrains=d["nb_terrains"],
        regles=ReglesScore(**d["regles"]),
        equipes=equipes,
        nb_poules=d.get("nb_poules", 1),
        nb_tours_brassage=d.get("nb_tours_brassage", 1),
        qualifies_principale_par_poule=d.get("qualifies_principale_par_poule", 1),
    )
    t._id_seq = d.get("_id_seq", 0)

    t.poules = [
        Poule(nom=p["nom"], phase=Phase(p["phase"]), tour=p.get("tour", 0),
              equipes=[par_id[i] for i in p["equipe_ids"]])
        for p in d["poules"]
    ]
    t.matchs = [
        Match(equipe_a=eq(m["equipe_a_id"]), equipe_b=eq(m["equipe_b_id"]),
              phase=Phase(m["phase"]),
              **{c: m.get(c) for c in _MATCH_CHAMPS})
        for m in d["matchs"]
    ]
    return t


def dumps(t: Tournoi) -> str:
    return json.dumps(to_dict(t), ensure_ascii=False, indent=2)


def loads(texte: str) -> Tournoi:
    return from_dict(json.loads(texte))
