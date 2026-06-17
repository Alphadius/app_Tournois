"""Page PUBLIQUE du tournoi (lecture seule) : planning + classement en direct.

À déployer séparément (Streamlit Community Cloud) avec comme fichier principal
`public.py`. Elle lit l'état du tournoi publié dans un Gist GitHub public — il n'y
a AUCUN widget de saisie, donc les participants ne peuvent rien modifier.

Réglages à fournir en secrets côté hébergement (pas de token nécessaire ici) :
  GIST_ID, GIST_USER  (voir sync.py)
"""
from __future__ import annotations

import streamlit as st

import sync
from engine import (
    Phase, classement_suisse, classements_phase, classements_tour, loads,
)

st.set_page_config(page_title="Tournoi — suivi en direct",
                   page_icon="🏐", layout="wide")

# Rafraîchissement (secondes) de la vue publique.
_REFRESH = 20


@st.cache_data(ttl=15, show_spinner=False)
def _charger_brut() -> str | None:
    return sync.recuperer()


def _label(m) -> str:
    return m.label_tour or m.poule or ""


def _ligne_match(m) -> dict:
    arbitre = "Auto-géré" if m.arbitre_auto else (m.arbitre.nom if m.arbitre else "—")
    return {
        "Terrain": m.terrain if m.terrain is not None else "—",
        "Phase": _label(m),
        "Équipe A": m.equipe_a.nom if m.equipe_a else "?",
        "Équipe B": m.equipe_b.nom if m.equipe_b else "?",
        "Arbitre": arbitre,
    }


def _tableau_matchs(matchs: list) -> None:
    lignes = [_ligne_match(m) for m in
              sorted(matchs, key=lambda m: (m.terrain or 99))]
    st.dataframe(lignes, use_container_width=True, hide_index=True)


def _classement(lignes: list) -> None:
    data = []
    for rang, l in enumerate(lignes, 1):
        data.append({
            "#": rang,
            "Équipe": l.equipe.nom,
            "J": l.joues,
            "V": l.victoires,
            "D": l.defaites,
            "Pts": l.points,
            "Δpts": l.ratio_points,
        })
    st.dataframe(data, use_container_width=True, hide_index=True)


def _section_classement(t) -> None:
    """Affiche les classements de la phase la plus avancée disponible."""
    poules_p = classements_phase(t, Phase.PRINCIPALE)
    poules_c = classements_phase(t, Phase.CONSOLANTE)
    if poules_p or poules_c:
        for titre, groupes in (("🏆 Principale", poules_p),
                               ("🥈 Consolante", poules_c)):
            if not groupes:
                continue
            st.markdown(f"#### {titre}")
            for nom, lignes in groupes.items():
                if len(groupes) > 1:
                    st.caption(nom)
                _classement(lignes)
        return

    # Système suisse : classement général cumulé (pas de poules de brassage).
    if getattr(t, "systeme", "poules") == "suisse":
        lignes = classement_suisse(t)
        if lignes:
            st.markdown("#### Classement général")
            _classement(lignes)
        else:
            st.caption("Classement disponible dès les premiers résultats.")
        return

    # Sinon (système à poules) : classements du dernier tour de brassage.
    tours = sorted({p.tour for p in t.poules if p.phase == Phase.BRASSAGE})
    if not tours:
        st.caption("Classement disponible dès les premiers résultats.")
        return
    dernier = tours[-1]
    groupes = classements_tour(t, dernier)
    st.markdown(f"#### Classement — tour {dernier}")
    for nom, lignes in groupes.items():
        if len(groupes) > 1:
            st.caption(nom)
        _classement(lignes)


@st.fragment(run_every=_REFRESH)
def vue() -> None:
    brut = _charger_brut()
    t = None
    if brut:
        try:
            t = loads(brut)
        except Exception:  # noqa: BLE001 - JSON vide / format inattendu
            t = None

    if t is None:
        st.info("⏳ En attente de données… Le planning s'affichera dès que "
                "l'organisateur aura publié le tournoi.")
        return

    st.title(f"🏐 {t.nom}")
    st.caption(f"Mise à jour automatique toutes les {_REFRESH} s.")

    # Matchs jouables non encore joués (les deux équipes connues).
    non_joues = [m for m in t.matchs
                 if not m.joue and m.equipe_a is not None and m.equipe_b is not None]
    vagues = sorted({m.vague for m in non_joues if m.vague is not None})
    courante = vagues[0] if vagues else None
    suivantes = set(vagues[1:3])
    en_cours = [m for m in non_joues if m.vague == courante]
    a_venir = [m for m in non_joues if m.vague in suivantes]

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🟢 Matchs en cours")
        if en_cours:
            _tableau_matchs(en_cours)
        else:
            st.caption("Aucun match en cours.")
    with col2:
        st.subheader("⏭️ Prochains matchs")
        if a_venir:
            _tableau_matchs(a_venir)
        else:
            st.caption("Rien de programmé pour l'instant.")

    st.divider()
    st.subheader("📊 Classement")
    _section_classement(t)


vue()
