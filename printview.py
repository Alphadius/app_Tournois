"""Génération d'une feuille HTML imprimable (planning + classement d'une phase).

Sortie autonome (CSS inclus) : on l'ouvre dans le navigateur puis Cmd/Ctrl+P
pour imprimer ou enregistrer en PDF. Affichage à l'écran masqué le bouton à
l'impression (@media print).
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from html import escape


def _nom(equipe) -> str:
    return escape(equipe.nom) if equipe is not None else "—"


def _score(m) -> str:
    if m.joue:
        return f"{m.points_a} : {m.points_b}"
    return "____ : ____"


_CSS = """
@page { margin: 1.4cm; }
* { box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
       color: #111; margin: 0; padding: 24px; }
h1 { font-size: 22px; margin: 0 0 2px; }
h2 { font-size: 15px; margin: 22px 0 6px; border-bottom: 2px solid #222;
     padding-bottom: 3px; }
.sub { color: #555; font-size: 12px; margin-bottom: 10px; }
table { width: 100%; border-collapse: collapse; font-size: 13px; margin-bottom: 8px; }
th, td { border: 1px solid #888; padding: 6px 9px; text-align: left; }
th { background: #eee; }
.terr { width: 80px; text-align: center; }
.arb { width: 130px; text-align: center; color: #555; }
.score { width: 120px; text-align: center; font-weight: 700; letter-spacing: 1px; }
.vs { color: #666; padding: 0 6px; }
.cols { display: flex; flex-wrap: wrap; gap: 24px; }
.cols > div { flex: 1; min-width: 240px; }
.btn { margin-bottom: 18px; padding: 8px 14px; font-size: 14px; cursor: pointer;
       border: 1px solid #333; border-radius: 6px; background: #fff; }
.cards { display: flex; flex-wrap: wrap; gap: 12px; margin: 6px 0 4px; }
.card { flex: 1; min-width: 130px; border: 1px solid #999; border-radius: 8px;
        padding: 10px 12px; background: #fafafa; }
.card .v { font-size: 22px; font-weight: 800; }
.card .l { font-size: 11px; color: #555; text-transform: uppercase;
           letter-spacing: .5px; }
.podium { font-size: 15px; margin: 4px 0; }
.fait { margin: 3px 0; font-size: 13px; }
.fait b { display: inline-block; min-width: 170px; color: #333; }
@media print { .btn { display: none; } body { padding: 0; } }
"""


def feuille_html(tournoi_nom: str, titre: str, matchs: list,
                 classements: dict, nb_terrains: int, regles=None) -> str:
    # --- planning groupé par vague ---
    par_vague: dict = defaultdict(list)
    for m in matchs:
        par_vague[m.vague].append(m)

    bloc_planning = ""
    for vague in sorted(par_vague, key=lambda v: (v is None, v)):
        lignes = ""
        for m in sorted(par_vague[vague], key=lambda x: x.terrain or 0):
            terrain = f"Terrain {m.terrain}" if m.terrain else "—"
            arbitre = getattr(m, "arbitre", None)
            if arbitre is not None:
                arb = _nom(arbitre)
            elif getattr(m, "arbitre_auto", False):
                arb = "Auto-géré"
            else:
                arb = "—"
            cible = ""
            if regles is not None:
                cible = f" — 🎯 {regles.points_cible(m.phase)} pts"
            lignes += (
                f"<tr><td class='terr'>{terrain}</td>"
                f"<td>{_nom(m.equipe_a)} <span class='vs'>vs</span> {_nom(m.equipe_b)}"
                f" <small>({escape(m.poule)}{cible})</small></td>"
                f"<td class='arb'>{arb}</td>"
                f"<td class='score'>{_score(m)}</td></tr>"
            )
        bloc_planning += (
            f"<h2>Vague {vague}</h2>"
            "<table><thead><tr><th class='terr'>Terrain</th>"
            "<th>Match</th><th class='arb'>Arbitre</th>"
            "<th class='score'>Score</th></tr></thead>"
            f"<tbody>{lignes}</tbody></table>"
        )

    # --- classements ---
    bloc_classements = ""
    if classements:
        cartes = ""
        for nom, lignes in classements.items():
            corps = ""
            for i, l in enumerate(lignes):
                corps += (
                    f"<tr><td>{i + 1}</td><td>{escape(l.equipe.nom)}</td>"
                    f"<td>{l.joues}</td><td>{l.victoires}</td>"
                    f"<td>{l.defaites}</td><td><b>{l.points}</b></td></tr>"
                )
            cartes += (
                f"<div><h2>{escape(nom)}</h2>"
                "<table><thead><tr><th>#</th><th>Équipe</th><th>J</th>"
                "<th>V</th><th>D</th><th>Pts</th></tr></thead>"
                f"<tbody>{corps}</tbody></table></div>"
            )
        bloc_classements = f"<div class='cols'>{cartes}</div>"

    date = datetime.now().strftime("%d/%m/%Y %H:%M")
    return f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8">
<title>{escape(tournoi_nom)} — {escape(titre)}</title>
<style>{_CSS}</style></head>
<body>
<button class="btn" onclick="window.print()">🖨️ Imprimer cette feuille</button>
<h1>{escape(tournoi_nom)}</h1>
<div class="sub">{escape(titre)} · {nb_terrains} terrain(s) · édité le {date}</div>
{bloc_planning}
{bloc_classements}
</body></html>"""


def _match_libelle(m) -> str:
    score = f"{m.points_a} – {m.points_b}" if m.joue else "—"
    return (f"{_nom(m.equipe_a)} {score} {_nom(m.equipe_b)} "
            f"<small>({escape(m.poule)})</small>")


def feuille_stats_html(stats: dict) -> str:
    """Feuille HTML récapitulative des statistiques du tournoi."""
    nom = escape(stats["nom"])
    syst = "Système suisse" if stats["systeme"] == "suisse" else "Poules de brassage"

    cartes = [
        ("Équipes", stats["nb_equipes"]),
        ("Matchs joués", stats["matchs_joues"]),
        ("Points joués", stats["points_total"]),
        ("Sets joués", stats["sets_total"]),
        ("Vagues", stats["nb_vagues"]),
        ("Pts / match", stats["points_moyen_par_match"]),
        ("Marge moy.", stats["marge_moyenne"]),
        ("Terrains", stats["nb_terrains"]),
    ]
    bloc_cards = "<div class='cards'>" + "".join(
        f"<div class='card'><div class='v'>{v}</div>"
        f"<div class='l'>{escape(str(l))}</div></div>" for l, v in cartes
    ) + "</div>"

    # --- podiums ---
    bloc_podium = ""
    medailles = {1: "🥇", 2: "🥈", 3: "🥉", 4: "4e"}
    lignes_pod = ""
    for groupe in ("Principale", "Consolante"):
        rangs = stats["podium"].get(groupe)
        if not rangs or 1 not in rangs:
            continue
        texte = " · ".join(
            f"{medailles[r]} {escape(rangs[r].nom)}"
            for r in (1, 2, 3, 4) if r in rangs)
        lignes_pod += f"<div class='podium'><b>{groupe}</b> — {texte}</div>"
    if lignes_pod:
        bloc_podium = f"<h2>Podiums</h2>{lignes_pod}"

    # --- faits marquants ---
    f = stats["faits"]
    faits = []
    if f.get("plus_large"):
        faits.append(("Plus large victoire", _match_libelle(f["plus_large"])))
    if f.get("plus_serre"):
        faits.append(("Match le plus serré", _match_libelle(f["plus_serre"])))
    if f.get("plus_prolifique"):
        faits.append(("Match le plus prolifique", _match_libelle(f["plus_prolifique"])))
    if f.get("meilleure_attaque"):
        d = f["meilleure_attaque"]
        faits.append(("Meilleure attaque",
                      f"{escape(d['equipe'].nom)} ({d['points_pour']} pts marqués)"))
    if f.get("meilleure_defense"):
        d = f["meilleure_defense"]
        moy = round(d["points_contre"] / d["joues"], 1) if d["joues"] else 0
        faits.append(("Meilleure défense",
                      f"{escape(d['equipe'].nom)} ({moy} pts encaissés / match)"))
    if f.get("plus_arbitre"):
        d = f["plus_arbitre"]
        faits.append(("A le plus arbitré",
                      f"{escape(d['equipe'].nom)} ({d['arbitrages']} matchs)"))
    bloc_faits = ""
    if faits:
        bloc_faits = "<h2>Faits marquants</h2>" + "".join(
            f"<div class='fait'><b>{escape(l)} :</b> {v}</div>" for l, v in faits)

    # --- bilan par phase ---
    bloc_phase = ""
    if stats["par_phase"]:
        corps = "".join(
            f"<tr><td>{escape(p['phase'])}</td><td>{p['matchs']}</td>"
            f"<td>{p['points']}</td></tr>" for p in stats["par_phase"])
        bloc_phase = ("<h2>Par phase</h2><table><thead><tr><th>Phase</th>"
                      "<th>Matchs</th><th>Points</th></tr></thead>"
                      f"<tbody>{corps}</tbody></table>")

    # --- classement complet des équipes ---
    afficher_byes = any(d["byes"] for d in stats["equipes"])
    th_byes = "<th>Byes</th>" if afficher_byes else ""
    lignes_eq = ""
    for i, d in enumerate(stats["equipes"]):
        col_byes = f"<td>{d['byes']}</td>" if afficher_byes else ""
        lignes_eq += (
            f"<tr><td>{i + 1}</td><td>{escape(d['equipe'].nom)}</td>"
            f"<td>{d['joues']}</td><td>{d['victoires']}</td><td>{d['defaites']}</td>"
            f"<td>{d['points_pour']}</td><td>{d['points_contre']}</td>"
            f"<td><b>{d['diff']:+d}</b></td><td>{d['arbitrages']}</td>{col_byes}</tr>"
        )
    bloc_equipes = (
        "<h2>Classement des équipes</h2>"
        "<table><thead><tr><th>#</th><th>Équipe</th><th>J</th><th>V</th><th>D</th>"
        "<th>Pts+</th><th>Pts−</th><th>Diff</th><th>Arb.</th>" + th_byes +
        f"</tr></thead><tbody>{lignes_eq}</tbody></table>"
    )

    date = datetime.now().strftime("%d/%m/%Y %H:%M")
    return f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8">
<title>{nom} — Statistiques</title>
<style>{_CSS}</style></head>
<body>
<button class="btn" onclick="window.print()">🖨️ Imprimer ce bilan</button>
<h1>📊 {nom} — bilan du tournoi</h1>
<div class="sub">{escape(syst)} · {stats['nb_equipes']} équipes · édité le {date}</div>
{bloc_cards}
{bloc_podium}
{bloc_faits}
{bloc_phase}
{bloc_equipes}
<div class="sub" style="margin-top:14px">J = joués · V = victoires · D = défaites ·
Pts+ marqués · Pts− encaissés · Arb. = matchs arbitrés</div>
</body></html>"""
