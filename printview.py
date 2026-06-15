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
            arb = _nom(arbitre) if arbitre is not None else "—"
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
