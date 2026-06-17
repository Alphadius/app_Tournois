"""Diffusion du tournoi vers un Gist GitHub (planning public en lecture seule).

Principe :
  - L'app locale (app.py) ÉCRIT l'état du tournoi dans un Gist via l'API GitHub,
    authentifiée par un token qui NE QUITTE JAMAIS la machine de l'organisateur.
  - L'app publique (public.py) LIT l'URL brute du Gist (public), SANS token : elle
    ne peut donc rien modifier — la saisie reste impossible côté participants.

Aucune dépendance externe : tout passe par la bibliothèque standard (urllib).

Configuration via `st.secrets` (fichier `.streamlit/secrets.toml`) ou, à défaut,
variables d'environnement :
  GIST_ID          identifiant du Gist                     (lecture + écriture)
  GIST_USER        login GitHub propriétaire du Gist       (lecture)
  GIST_TOKEN       token GitHub avec le scope "gist"       (écriture seulement)
  GIST_FILE        nom du fichier dans le Gist             (défaut "tournoi.json")
  APP_PUBLIQUE_URL URL de l'app Streamlit publique         (affichage du lien)
"""
from __future__ import annotations

import json
import os
import time
import urllib.request

_API = "https://api.github.com/gists/"
_FICHIER_DEFAUT = "tournoi.json"


def _config(cle: str, defaut: str | None = None) -> str | None:
    """Lit un réglage : priorité aux secrets Streamlit, repli sur l'environnement."""
    try:
        import streamlit as st
        if cle in st.secrets:
            return str(st.secrets[cle])
    except Exception:  # noqa: BLE001 - pas de secrets.toml, ou Streamlit absent
        pass
    return os.environ.get(cle, defaut)


def _fichier() -> str:
    return _config("GIST_FILE", _FICHIER_DEFAUT) or _FICHIER_DEFAUT


def configure_ecriture() -> bool:
    """Vrai si la publication est possible (identifiant + token présents)."""
    return bool(_config("GIST_ID") and _config("GIST_TOKEN"))


def configure_lecture() -> bool:
    """Vrai si la lecture publique est possible (identifiant + login présents)."""
    return bool(_config("GIST_ID") and _config("GIST_USER"))


def url_brute() -> str | None:
    """URL brute publique du fichier JSON dans le Gist (source de données)."""
    gid, user = _config("GIST_ID"), _config("GIST_USER")
    if not (gid and user):
        return None
    return f"https://gist.githubusercontent.com/{user}/{gid}/raw/{_fichier()}"


def app_publique_url() -> str | None:
    """URL de l'app Streamlit publique à partager aux participants (si configurée)."""
    return _config("APP_PUBLIQUE_URL")


def publier(contenu_json: str) -> bool:
    """Pousse le contenu JSON dans le Gist (PATCH). Renvoie True si réussi.

    Ne lève jamais d'exception : en cas de souci (hors-ligne, token invalide,
    quota…) renvoie simplement False, pour ne jamais perturber l'app locale.
    """
    gid, token = _config("GIST_ID"), _config("GIST_TOKEN")
    if not (gid and token):
        return False
    corps = json.dumps({"files": {_fichier(): {"content": contenu_json}}}).encode()
    req = urllib.request.Request(_API + gid, data=corps, method="PATCH")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return 200 <= r.status < 300
    except Exception:  # noqa: BLE001 - publication best-effort
        return False


def recuperer() -> str | None:
    """Récupère le contenu JSON du Gist (lecture publique, sans token).

    Ajoute un paramètre anti-cache (qui change toutes les 20 s) pour limiter la
    latence du CDN GitHub. Renvoie None si indisponible.
    """
    url = url_brute()
    if not url:
        return None
    cb = int(time.time() // 20)
    sep = "&" if "?" in url else "?"
    try:
        with urllib.request.urlopen(f"{url}{sep}cb={cb}", timeout=10) as r:
            return r.read().decode("utf-8")
    except Exception:  # noqa: BLE001 - lecture best-effort
        return None
