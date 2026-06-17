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
import urllib.error
import urllib.request

_API = "https://api.github.com/gists/"
_FICHIER_DEFAUT = "tournoi.json"

# Détail de la dernière erreur de publication (pour un message clair à l'écran).
_DERNIERE_ERREUR: str | None = None
# Instant (time.monotonic) avant lequel on ne RETENTE PAS d'écrire, pour respecter
# la limite secondaire de GitHub (toute requête pendant le blocage le prolonge).
_BLOQUE_JUSQUA: float = 0.0


def derniere_erreur() -> str | None:
    """Message lisible expliquant le dernier échec de `publier` (ou None)."""
    return _DERNIERE_ERREUR


def secondes_avant_retry() -> int:
    """Secondes restantes avant de pouvoir réessayer de publier (0 si possible)."""
    import math
    return max(0, math.ceil(_BLOQUE_JUSQUA - time.monotonic()))


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
    global _DERNIERE_ERREUR, _BLOQUE_JUSQUA
    _DERNIERE_ERREUR = None
    gid, token = _config("GIST_ID"), _config("GIST_TOKEN")
    if not (gid and token):
        _DERNIERE_ERREUR = "Diffusion non configurée (GIST_ID / GIST_TOKEN manquant)."
        return False
    # Si GitHub nous a demandé d'attendre, on ne retente pas avant la fin du délai
    # (toute requête prématurée prolongerait le blocage côté serveur).
    restant = secondes_avant_retry()
    if restant > 0:
        _DERNIERE_ERREUR = (f"Limite GitHub : attends encore {restant} s avant de "
                            "republier (réessayer maintenant prolonge le blocage).")
        return False
    corps = json.dumps({"files": {_fichier(): {"content": contenu_json}}}).encode()
    req = urllib.request.Request(_API + gid, data=corps, method="PATCH")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return 200 <= r.status < 300
    except urllib.error.HTTPError as e:  # réponse GitHub avec un code d'erreur
        try:
            detail = e.read().decode("utf-8", "replace").lower()
        except Exception:  # noqa: BLE001
            detail = ""
        if e.code in (403, 429) and "rate limit" in detail:
            # GitHub indique parfois combien de temps patienter (Retry-After, en
            # secondes). La limite secondaire « anti-abus » n'envoie souvent RIEN
            # et reste active plusieurs minutes (toute requête la relance) : à
            # défaut d'en-tête, on patiente donc plus longtemps (180 s).
            try:
                attente = int(e.headers.get("Retry-After"))
            except (TypeError, ValueError):
                attente = 180
            attente = max(attente, 60)
            _BLOQUE_JUSQUA = time.monotonic() + attente
            _DERNIERE_ERREUR = ("Limite de requêtes GitHub atteinte : arrête de "
                                f"publier {attente} s (chaque essai prolonge le "
                                "blocage), puis réessaie.")
        elif e.code in (401, 403):
            _DERNIERE_ERREUR = ("Accès refusé par GitHub : vérifie que le token "
                                "(classique, scope « gist ») est valide.")
        elif e.code == 404:
            _DERNIERE_ERREUR = "Gist introuvable : vérifie GIST_ID."
        else:
            _DERNIERE_ERREUR = f"GitHub a répondu une erreur {e.code}."
        return False
    except Exception:  # noqa: BLE001 - hors-ligne, DNS, timeout…
        _DERNIERE_ERREUR = "Pas de connexion à GitHub (réseau indisponible ?)."
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
