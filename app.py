"""Interface Streamlit minimale pour gérer un tournoi de volley.

Déroulé : tours de brassage (poules re-réparties par niveau) -> poules
principale / consolante -> phase éliminatoire (un bracket par groupe).

Lancement :  streamlit run app.py
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import streamlit as st

from engine import (
    Phase, ReglesScore, bye_du_tour, classement_suisse, classements_tour,
    creer_tournoi, dumps, elimination_creee, enregistrer_set_sec,
    generer_elimination, generer_poules_finales, generer_tour_brassage_suivant,
    lancer_tour_brassage, loads, maj_regles, nb_tours_recommande, podium,
    poules_finales_creees, poules_finales_terminees, suisse_termine,
    tour_brassage_termine, tour_suisse_termine, tours_suisse,
)
from engine.ranking import classement_poule
from printview import feuille_html

st.set_page_config(page_title="Tournoi Volley", page_icon="🏐", layout="wide")


AUTOSAVE = Path(__file__).parent / ".autosave" / "dernier.json"


def tournoi():
    return st.session_state.get("tournoi")


def autosave(t) -> None:
    """Écrit l'état complet sur disque (silencieux en cas d'erreur d'écriture)."""
    try:
        AUTOSAVE.parent.mkdir(parents=True, exist_ok=True)
        AUTOSAVE.write_text(dumps(t), encoding="utf-8")
    except Exception:  # noqa: BLE001 - la sauvegarde auto ne doit jamais planter l'UI
        pass


def restaurer_autosave():
    """Recharge la dernière session si elle existe. Supprime un fichier corrompu."""
    if not AUTOSAVE.exists():
        return None
    try:
        return loads(AUTOSAVE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - autosave illisible (ancien format, etc.)
        try:
            AUTOSAVE.unlink()
        except OSError:
            pass
        return None


def reset():
    """Revient à l'écran de création SANS supprimer la sauvegarde auto.

    On vide juste la session et on lève un drapeau pour forcer l'écran de
    création (sinon `main()` restaurerait aussitôt l'ancien tournoi). La
    sauvegarde n'est écrasée que si un nouveau tournoi est réellement créé.
    """
    st.session_state.pop("tournoi", None)
    st.session_state["forcer_creation"] = True


def charger_fichier(uploaded) -> bool:
    """Charge un tournoi depuis un fichier .json téléversé. True si succès."""
    try:
        st.session_state["tournoi"] = loads(uploaded.getvalue().decode("utf-8"))
        st.session_state.pop("forcer_creation", None)
        return True
    except Exception as e:  # noqa: BLE001 - on remonte l'erreur à l'utilisateur
        st.error(f"Fichier invalide : {e}")
        return False


# --------------------------------------------------------------------------- #
#  Écran 1 : création
# --------------------------------------------------------------------------- #
def ecran_creation():
    st.title("🏐 Nouveau tournoi de volley")
    st.caption("Configure le tournoi, puis lance le premier tour de brassage.")

    dernier = restaurer_autosave()
    if dernier is not None:
        st.info(f"💾 Dernier tournoi en sauvegarde auto : **{dernier.nom}**")
        if st.button("↩️ Reprendre le dernier tournoi", type="primary",
                     use_container_width=True):
            st.session_state["tournoi"] = dernier
            st.session_state.pop("forcer_creation", None)
            st.rerun()

    with st.expander("📂 Reprendre un tournoi sauvegardé (.json)"):
        fichier = st.file_uploader("Fichier du tournoi", type=["json"],
                                   key="upload_creation", label_visibility="collapsed")
        if fichier is not None and st.button("Charger ce tournoi"):
            if charger_fichier(fichier):
                st.rerun()

    # Le choix du système est HORS du formulaire : sa sélection déclenche un
    # rerun qui adapte les champs affichés (impossible dans un st.form figé).
    systeme_label = st.radio(
        "Système de la phase de classement",
        ["Poules de brassage", "Système suisse"], horizontal=True,
        help="• Poules de brassage : poules re-réparties par niveau à chaque tour.\n"
             "• Système suisse : à chaque tour, on oppose des équipes de niveau "
             "proche, sans rejouer le même adversaire.")
    systeme = "suisse" if systeme_label == "Système suisse" else "poules"

    with st.form("creation"):
        col1, col2 = st.columns(2)
        with col1:
            nom = st.text_input("Nom du tournoi", "Tournoi du club")
            nb_equipes = st.number_input("Nombre d'équipes", 2, 64, 8, step=1)
            nb_terrains = st.number_input("Terrains (matchs en parallèle)", 1, 16, 3, step=1)
            if systeme == "poules":
                nb_poules = st.number_input("Poules par tour de brassage", 1, 16, 2, step=1)
                nb_tours = st.number_input(
                    "Tours de brassage", 1, 6, 1, step=1,
                    help="Après chaque tour, les équipes sont re-réparties dans de "
                         "nouvelles poules selon le classement (poules de niveau).")
                suisse_illimite, suisse_tours = True, 1
            else:
                nb_poules, nb_tours = 1, 1
                suisse_illimite = st.checkbox(
                    "Nombre de tours illimité", value=True,
                    help="Coché : on enchaîne les tours jusqu'à ce qu'une seule "
                         "équipe reste invaincue. Décoché : nombre de tours fixé.")
                suisse_tours = st.number_input(
                    "Nombre de tours (si fixé)", 1, 30,
                    nb_tours_recommande(int(nb_equipes)), step=1,
                    help=f"Recommandé pour départager un vainqueur : "
                         f"~{nb_tours_recommande(int(nb_equipes))} tours.")
        with col2:
            if systeme == "poules":
                qualifies = st.number_input(
                    "Qualifiés en principale (par poule du dernier tour)", 1, 32, 2, step=1,
                    help="Les meilleurs de chaque poule montent en principale, "
                         "les autres en consolante.")
            else:
                qualifies = 1
                st.caption("ℹ️ En système suisse : la **moitié haute** du classement "
                           "va en principale, la moitié basse en consolante.")
            points_gagner = st.number_input(
                "Points pour gagner un match (set sec)", 1, 99, 25, step=1)
            pts_v = st.number_input("Points de classement / victoire", 0, 10, 3, step=1)
            pts_d = st.number_input("Points de classement / défaite", 0, 10, 0, step=1)
            aller_retour = (st.checkbox("Aller-retour (matchs en double)", value=False)
                            if systeme == "poules" else False)

        st.markdown("**Noms des équipes** (un par ligne, vide = noms automatiques)")
        noms_brut = st.text_area("Équipes", height=140, label_visibility="collapsed",
                                 placeholder="Les Aigles\nLes Tigres\n...")
        submit = st.form_submit_button("🏐 Créer le tournoi", type="primary")

    if submit:
        noms = [n for n in noms_brut.splitlines() if n.strip()]
        if not noms:
            noms = [f"Équipe {i}" for i in range(1, int(nb_equipes) + 1)]
        regles = ReglesScore(
            format_match="set_sec", points_pour_gagner=int(points_gagner),
            points_victoire=int(pts_v), points_defaite=int(pts_d),
            aller_retour=aller_retour)
        suisse_nb_tours = 0 if suisse_illimite else int(suisse_tours)
        try:
            t = creer_tournoi(
                nom=nom, noms_equipes=noms, nb_poules=int(nb_poules),
                nb_terrains=int(nb_terrains), nb_tours_brassage=int(nb_tours),
                regles=regles, qualifies_principale_par_poule=int(qualifies),
                systeme=systeme, suisse_nb_tours=suisse_nb_tours)
            lancer_tour_brassage(t, 1)
            st.session_state["tournoi"] = t
            # Création effective : on quitte le mode "écran de création" et la
            # sauvegarde auto sera écrasée par ce nouveau tournoi au prochain rendu.
            st.session_state.pop("forcer_creation", None)
            autosave(t)
            st.rerun()
        except ValueError as e:
            st.error(str(e))


# --------------------------------------------------------------------------- #
#  Réglages (barre latérale)
# --------------------------------------------------------------------------- #
def sidebar_reglages(t):
    with st.sidebar:
        st.header("⚙️ Réglages")
        st.caption(f"Tournoi : **{t.nom}**")
        with st.form("reglages"):
            st.markdown("**Scoring**")
            ppg = st.number_input("Points pour gagner un match", 1, 99,
                                  t.regles.points_pour_gagner, step=1)
            pv = st.number_input("Points de classement / victoire", 0, 10,
                                 t.regles.points_victoire, step=1)
            pd = st.number_input("Points de classement / défaite", 0, 10,
                                 t.regles.points_defaite, step=1)
            criteres = {
                "points": "Points de classement",
                "confrontation": "Confrontation directe",
                "ratio_points": "Différence de points (Δpts)",
                "ratio_sets": "Différence de sets",
            }
            ordre = st.multiselect(
                "Départage (du + au - prioritaire)", options=list(criteres),
                default=t.regles.departage, format_func=lambda k: criteres[k])
            if st.form_submit_button("💾 Appliquer", type="primary",
                                     use_container_width=True):
                maj_regles(t, points_pour_gagner=int(ppg), points_victoire=int(pv),
                           points_defaite=int(pd), departage=ordre or t.regles.departage)
                st.rerun()

        st.divider()
        st.markdown("**Sauvegarde**")
        st.caption("✅ Sauvegarde auto active — l'état est restauré au rechargement "
                   "de la page. Le bouton ci-dessous exporte une copie.")
        nom_fichier = t.nom.strip().replace(" ", "_") or "tournoi"
        st.download_button("💾 Télécharger (.json)", data=dumps(t),
                           file_name=f"{nom_fichier}.json", mime="application/json",
                           use_container_width=True)
        fichier = st.file_uploader("📂 Charger un autre tournoi", type=["json"],
                                   key="upload_sidebar")
        if fichier is not None and st.button("Remplacer par ce fichier",
                                             use_container_width=True):
            if charger_fichier(fichier):
                st.rerun()

        st.divider()
        st.markdown("**Affichage**")
        st.checkbox("Afficher la colonne Δpts", key="show_dpts", value=False)

        st.divider()
        st.caption("ℹ️ Format : 1 set sec. Le nb de terrains, de poules et de "
                   "tours de brassage est figé à la création.")
        if st.button("🔄 Nouveau tournoi", use_container_width=True):
            reset()
            st.rerun()


# --------------------------------------------------------------------------- #
#  Composants d'affichage
# --------------------------------------------------------------------------- #
def _nom(equipe):
    return equipe.nom if equipe is not None else "— à déterminer —"


def carte_match(t, m, contexte: str):
    """Affiche un match avec saisie de score (set sec)."""
    if not m.pret:
        st.markdown(f"⏸️ *{_nom(m.equipe_a)}* vs *{_nom(m.equipe_b)}*")
        st.caption("En attente du tour précédent")
        st.divider()
        return
    etat = "✅" if m.joue else "⏳"
    lieu = f"Terrain {m.terrain}" if m.terrain else ""
    st.markdown(f"{etat} *{lieu}* — {m.poule}")
    c1, c2 = st.columns(2)
    pa = c1.number_input(_nom(m.equipe_a), 0, 99,
                         value=m.points_a if m.points_a is not None else 0,
                         key=f"pa_{contexte}_{m.id}")
    pb = c2.number_input(_nom(m.equipe_b), 0, 99,
                         value=m.points_b if m.points_b is not None else 0,
                         key=f"pb_{contexte}_{m.id}")
    if st.button("Enregistrer", key=f"btn_{contexte}_{m.id}", use_container_width=True):
        if pa == pb:
            st.warning("Égalité impossible : il faut un vainqueur.")
        else:
            enregistrer_set_sec(t, m.id, int(pa), int(pb))
            st.rerun()
    st.divider()


def bouton_impression(t, titre: str, matchs, classements, cle: str):
    """Bouton de téléchargement d'une feuille HTML imprimable (planning + classement)."""
    if not matchs:
        return
    html = feuille_html(t.nom, titre, matchs, classements, t.nb_terrains)
    nom_fichier = f"planning_{titre}".lower().replace(" ", "_").replace("·", "")
    st.download_button(
        "🖨️ Planning imprimable (.html)", data=html,
        file_name=f"{nom_fichier}.html", mime="text/html",
        key=f"print_{cle}",
        help="Télécharge une feuille à ouvrir puis imprimer (Cmd/Ctrl+P), "
             "ou enregistrer en PDF.")


def afficher_planning(t, matchs, titre: str, contexte: str):
    if not matchs:
        return
    st.subheader(titre)
    par_vague = defaultdict(list)
    for m in matchs:
        par_vague[m.vague].append(m)
    for vague in sorted(par_vague, key=lambda v: (v is None, v)):
        ms = par_vague[vague]
        joues = sum(1 for m in ms if m.joue)
        st.markdown(f"**Vague {vague}**  ·  {joues}/{len(ms)} joués")
        cols = st.columns(max(t.nb_terrains, 1))
        for m in sorted(ms, key=lambda x: x.terrain or 0):
            with cols[(m.terrain or 1) - 1]:
                carte_match(t, m, contexte)


def afficher_classements(classements: dict, titre: str):
    if not classements:
        return
    st.subheader(titre)
    montrer_dpts = st.session_state.get("show_dpts", False)
    cols = st.columns(len(classements))
    for col, (nom, lignes) in zip(cols, classements.items()):
        with col:
            st.markdown(f"**{nom}**")
            data = []
            for i, l in enumerate(lignes):
                ligne = {"#": i + 1, "Équipe": l.equipe.nom, "J": l.joues,
                         "V": l.victoires, "D": l.defaites, "Pts": l.points}
                if montrer_dpts:
                    ligne["Δpts"] = l.ratio_points
                data.append(ligne)
            st.dataframe(data, hide_index=True, use_container_width=True)


def _ordre_label(m) -> int:
    # Dans la dernière colonne, on affiche la Finale avant la Petite finale.
    return 1 if m.label_tour == "Petite finale" else 0


def afficher_bracket(t, groupe: str):
    matchs = [m for m in t.matchs_de(Phase.ELIMINATION) if m.groupe == groupe]
    if not matchs:
        return
    st.markdown(f"### 🏆 {groupe}")
    par_tour = defaultdict(list)
    for m in matchs:
        par_tour[m.tour_elim].append(m)
    cols = st.columns(len(par_tour))
    for col, te in zip(cols, sorted(par_tour)):
        with col:
            for m in sorted(par_tour[te], key=_ordre_label):
                st.markdown(f"**{m.label_tour or f'Tour {te}'}**")
                carte_match(t, m, contexte=f"elim_{groupe}")


# --------------------------------------------------------------------------- #
#  Écran 2 : gestion du tournoi (flux par étapes)
# --------------------------------------------------------------------------- #
def onglet_brassage(t, tour: int):
    classements = classements_tour(t, tour)
    afficher_classements(classements, f"Classements — Brassage {tour}")
    bouton_impression(t, f"Brassage {tour}", t.matchs_tour(tour), classements,
                      cle=f"brass_{tour}")
    afficher_planning(t, t.matchs_tour(tour), "Planning des matchs", f"brass_{tour}")

    if not tour_brassage_termine(t, tour):
        restants = sum(1 for m in t.matchs_tour(tour) if not m.joue)
        st.info(f"Termine ce tour pour continuer ({restants} match(s) restant(s)).")
        return

    st.success(f"Brassage {tour} terminé ✅")
    if tour < t.nb_tours_brassage:
        if not t.poules_tour(tour + 1):
            if st.button(f"➡️ Lancer le brassage {tour + 1} (re-répartition)",
                         type="primary", key=f"next_{tour}"):
                generer_tour_brassage_suivant(t, tour)
                st.rerun()
        else:
            st.caption(f"Brassage {tour + 1} déjà lancé (onglet suivant).")
    else:
        if not poules_finales_creees(t):
            if st.button("🏁 Générer poule principale & consolante",
                         type="primary", key="gen_finales"):
                generer_poules_finales(t)
                st.rerun()
        else:
            st.caption("Poules finales déjà créées (onglet Finales).")


def onglet_suisse(t, tour: int):
    cl = classement_suisse(t)
    afficher_classements({"Classement général (système suisse)": cl},
                         f"Classement après le tour {tour}")
    bye = bye_du_tour(t, tour)
    if bye is not None:
        st.info(f"🎟️ **{bye.nom}** est exemptée ce tour (victoire offerte).")
    matchs = t.matchs_tour(tour)
    bouton_impression(t, f"Suisse Tour {tour}", matchs,
                      {"Classement général": cl}, cle=f"suisse_{tour}")
    afficher_planning(t, matchs, "Planning des matchs", f"suisse_{tour}")

    if not tour_suisse_termine(t, tour):
        restants = sum(1 for m in matchs if not m.joue)
        st.info(f"Termine ce tour pour continuer ({restants} match(s) restant(s)).")
        return

    st.success(f"Tour {tour} terminé ✅")
    if suisse_termine(t):
        if not poules_finales_creees(t):
            st.success("🏁 Système suisse terminé.")
            if st.button("🏁 Générer poule principale & consolante",
                         type="primary", key="gen_finales_suisse"):
                generer_poules_finales(t)
                st.rerun()
        else:
            st.caption("Poules finales déjà créées (onglet Finales).")
    elif tour == max(tours_suisse(t)):
        if st.button(f"➡️ Générer le tour {tour + 1} (appariement par niveau)",
                     type="primary", key=f"next_suisse_{tour}"):
            generer_tour_brassage_suivant(t, tour)
            st.rerun()
    else:
        st.caption(f"Tour {tour + 1} déjà lancé (onglet suivant).")


def onglet_finales(t):
    classements = {
        p.nom: classement_poule(p, t.matchs, t.regles)
        for p in t.poules if p.phase in (Phase.PRINCIPALE, Phase.CONSOLANTE)
    }
    afficher_classements(classements, "Classements des poules finales")
    matchs = t.matchs_de(Phase.PRINCIPALE) + t.matchs_de(Phase.CONSOLANTE)
    bouton_impression(t, "Poules finales", matchs, classements, cle="finales")
    afficher_planning(t, matchs, "Planning — Finales", "finales")

    if not poules_finales_terminees(t):
        restants = sum(1 for m in matchs if not m.joue)
        st.info(f"Termine les poules finales pour lancer l'élimination "
                f"({restants} match(s) restant(s)).")
        return
    st.success("Poules finales terminées ✅")
    if not elimination_creee(t):
        if st.button("🥇 Générer la phase éliminatoire", type="primary"):
            generer_elimination(t)
            st.rerun()


def onglet_elimination(t):
    medailles = {1: "🥇", 2: "🥈", 3: "🥉", 4: "4e"}
    pod = podium(t)
    for groupe in ("Principale", "Consolante"):
        if groupe in pod and 1 in pod[groupe]:
            classement = pod[groupe]
            texte = "  ·  ".join(
                f"{medailles[r]} {classement[r].nom}"
                for r in (1, 2, 3, 4) if r in classement)
            st.success(f"**{groupe}** — {texte}")
    for groupe in ("Principale", "Consolante"):
        if any(m.groupe == groupe for m in t.matchs_de(Phase.ELIMINATION)):
            afficher_bracket(t, groupe)
            st.divider()


def ecran_tournoi(t):
    sidebar_reglages(t)
    est_suisse = getattr(t, "systeme", "poules") == "suisse"
    st.title(f"🏐 {t.nom}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Équipes", len(t.equipes))
    c2.metric("Terrains", t.nb_terrains)
    if est_suisse:
        mode = "illimité" if getattr(t, "suisse_nb_tours", 0) == 0 \
            else f"{t.suisse_nb_tours} tours"
        c3.metric("Système suisse", mode)
    else:
        c3.metric("Tours brassage", t.nb_tours_brassage)
    c4.metric("Pts pour gagner", t.regles.points_pour_gagner)

    # Les tours de classement sont dérivés des matchs (vaut pour poules ET suisse).
    tours = sorted({m.tour for m in t.matchs if m.phase == Phase.BRASSAGE and m.tour})
    prefixe = "Tour" if est_suisse else "Brassage"
    labels = [f"{prefixe} {n}" for n in tours]
    if poules_finales_creees(t):
        labels.append("Finales")
    if elimination_creee(t):
        labels.append("Élimination")

    onglets = st.tabs(labels)
    idx = 0
    for n in tours:
        with onglets[idx]:
            if est_suisse:
                onglet_suisse(t, n)
            else:
                onglet_brassage(t, n)
        idx += 1
    if poules_finales_creees(t):
        with onglets[idx]:
            onglet_finales(t)
        idx += 1
    if elimination_creee(t):
        with onglets[idx]:
            onglet_elimination(t)
        idx += 1

    # Sauvegarde automatique de l'état courant à chaque interaction.
    autosave(t)


def main():
    t = tournoi()
    # Si l'utilisateur a demandé un nouveau tournoi, on n'auto-restaure pas :
    # on le laisse sur l'écran de création (la sauvegarde du précédent reste
    # intacte tant qu'il n'a pas créé le nouveau).
    if t is None and not st.session_state.get("forcer_creation"):
        t = restaurer_autosave()
        if t is not None:
            st.session_state["tournoi"] = t
            st.toast("Session restaurée depuis la sauvegarde automatique 💾")
    if t is None:
        ecran_creation()
    else:
        ecran_tournoi(t)


if __name__ == "__main__":
    main()
