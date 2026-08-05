"""
Tests unitaires pour stats_service.get_stats()
Utilise une DB SQLite en mémoire — pas de vraie DB touchée
"""
import json
import sqlite3
import pytest
from unittest.mock import patch
from datetime import date, timedelta


# ── Helpers ──────────────────────────────────────────
def make_db():
    """
    Crée une DB SQLite en mémoire avec le même schéma que la vraie base.
    get_stats() lit analyses ET resolutions (les erreurs résolues sont exclues
    des stats), donc les deux tables doivent exister.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE analyses (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            date       TEXT NOT NULL,
            fichier    TEXT NOT NULL,
            erreurs    TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE resolutions (
            signature   TEXT PRIMARY KEY,
            resolved_at TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def insert_analyse(conn, date_str: str, fichier: str, erreurs: list):
    conn.execute(
        "INSERT INTO analyses (date, fichier, erreurs, created_at) VALUES (?, ?, ?, ?)",
        (date_str, fichier, json.dumps(erreurs), f"{date_str}T10:00:00")
    )
    conn.commit()


def marquer_resolue(conn, fichier: str, ligne: int, niveau: str):
    """Marque résolue l'erreur située à (fichier, ligne, niveau)."""
    from backend.models.schemas import signature_erreur
    conn.execute(
        "INSERT OR IGNORE INTO resolutions (signature, resolved_at) VALUES (?, ?)",
        (signature_erreur(fichier, ligne, niveau), "2026-01-01T10:00:00")
    )
    conn.commit()


def get_stats_avec(conn, *args, **kwargs):
    """Appelle get_stats() branché sur la DB de test."""
    with patch("backend.services.sqlite_service.get_connexion", return_value=conn):
        from importlib import reload
        import backend.services.stats_service as ss
        reload(ss)
        return ss.get_stats(*args, **kwargs)


ERREUR_CRITIQUE = {
    "niveau": "critique", "titre": "Fonction trop longue",
    "ligne": 1, "description": "desc", "extrait": "x", "cours": []
}

ERREUR_AVERTISSEMENT = {
    "niveau": "avertissement", "titre": "Variable non typée",
    "ligne": 5, "description": "desc", "extrait": "y", "cours": []
}


# ── Tests ─────────────────────────────────────────────
def test_stats_db_vide():
    """DB vide → total_erreurs = 0"""
    conn = make_db()
    with patch("backend.services.sqlite_service.get_connexion", return_value=conn):
        from backend.services.stats_service import get_stats
        result = get_stats("semaine")
    assert result.total_erreurs == 0
    assert result.total_fichiers == 0


def test_stats_compte_erreurs():
    """2 erreurs insérées → total_erreurs = 2"""
    conn = make_db()
    today = date.today().isoformat()
    insert_analyse(conn, today, "main.py", [ERREUR_CRITIQUE, ERREUR_AVERTISSEMENT])

    with patch("backend.services.sqlite_service.get_connexion", return_value=conn):
        from importlib import reload
        import backend.services.stats_service as ss
        reload(ss)
        result = ss.get_stats("semaine")

    assert result.total_erreurs == 2


def test_stats_compte_fichiers():
    """2 fichiers différents → total_fichiers = 2"""
    conn = make_db()
    today = date.today().isoformat()
    insert_analyse(conn, today, "main.py",    [ERREUR_CRITIQUE])
    insert_analyse(conn, today, "service.py", [ERREUR_AVERTISSEMENT])

    with patch("backend.services.sqlite_service.get_connexion", return_value=conn):
        import backend.services.stats_service as ss
        from importlib import reload
        reload(ss)
        result = ss.get_stats("semaine")

    assert result.total_fichiers == 2


def test_stats_periode_semaine():
    """periode=semaine → 7 points dans la courbe"""
    conn = make_db()
    with patch("backend.services.sqlite_service.get_connexion", return_value=conn):
        import backend.services.stats_service as ss
        from importlib import reload
        reload(ss)
        result = ss.get_stats("semaine")
    assert len(result.courbe) == 7


def test_stats_periode_mois():
    """periode=mois → 30 points dans la courbe"""
    conn = make_db()
    with patch("backend.services.sqlite_service.get_connexion", return_value=conn):
        import backend.services.stats_service as ss
        from importlib import reload
        reload(ss)
        result = ss.get_stats("mois")
    assert len(result.courbe) == 30


def test_stats_offset_decale_fenetre():
    """offset=1 → ne voit pas les données d'aujourd'hui"""
    conn = make_db()
    today = date.today().isoformat()
    insert_analyse(conn, today, "main.py", [ERREUR_CRITIQUE])

    with patch("backend.services.sqlite_service.get_connexion", return_value=conn):
        import backend.services.stats_service as ss
        from importlib import reload
        reload(ss)
        result = ss.get_stats("semaine", offset=1)

    assert result.total_erreurs == 0


def test_stats_top3_erreurs():
    """
    Top 3 erreurs récurrentes : « occurrences » compte les JOURS de détection.
    3 re-scans du même fichier le même jour = 1 occurrence, pas 3.
    """
    conn = make_db()
    today = date.today().isoformat()
    # Insère 3 fois la même erreur critique, le même jour
    for _ in range(3):
        insert_analyse(conn, today, "main.py", [ERREUR_CRITIQUE])

    result = get_stats_avec(conn, "semaine")

    assert len(result.erreurs_recurrentes) == 1
    assert result.erreurs_recurrentes[0].occurrences == 1


def test_stats_erreur_recurrente_sur_plusieurs_jours():
    """Une erreur qui revient 3 jours de suite → 3 occurrences"""
    conn = make_db()
    today = date.today()
    for delta in (2, 1, 0):
        jour = (today - timedelta(days=delta)).isoformat()
        insert_analyse(conn, jour, "main.py", [ERREUR_CRITIQUE])

    result = get_stats_avec(conn, "semaine")

    assert result.erreurs_recurrentes[0].occurrences == 3


def test_stats_rescans_du_meme_jour_ne_gonflent_pas_la_courbe():
    """
    3 re-scans du même fichier → la courbe du jour affiche 1 erreur, comme le
    rapport du même jour. Les deux pages doivent donner le même chiffre.
    """
    conn = make_db()
    today = date.today().isoformat()
    for _ in range(3):
        insert_analyse(conn, today, "main.py", [ERREUR_CRITIQUE])

    result = get_stats_avec(conn, "semaine")

    assert result.courbe[-1].critiques == 1
    assert result.courbe[-1].total_erreurs == 1
    assert result.total_erreurs == 1


def test_stats_total_egale_la_somme_de_la_courbe():
    """Invariant : la stat card « Total erreurs » = somme des points de la courbe"""
    conn = make_db()
    today = date.today()
    insert_analyse(conn, (today - timedelta(days=1)).isoformat(), "a.py", [ERREUR_CRITIQUE])
    insert_analyse(conn, today.isoformat(), "a.py", [ERREUR_CRITIQUE, ERREUR_AVERTISSEMENT])
    insert_analyse(conn, today.isoformat(), "a.py", [ERREUR_CRITIQUE])  # re-scan

    result = get_stats_avec(conn, "semaine")

    assert result.total_erreurs == sum(p.total_erreurs for p in result.courbe)


# ── Résolutions ───────────────────────────────────────
def test_stats_exclut_les_erreurs_resolues():
    """Une erreur marquée résolue sort du total et de la courbe"""
    conn = make_db()
    today = date.today().isoformat()
    insert_analyse(conn, today, "main.py", [ERREUR_CRITIQUE, ERREUR_AVERTISSEMENT])
    marquer_resolue(conn, "main.py", ERREUR_CRITIQUE["ligne"], "critique")

    result = get_stats_avec(conn, "semaine")

    assert result.total_erreurs == 1      # seul l'avertissement reste ouvert
    assert result.total_resolues == 1
    assert result.courbe[-1].critiques == 0
    assert result.courbe[-1].avertissements == 1


def test_stats_resolue_compte_une_seule_fois():
    """Re-scannée 3 fois puis résolue → comptée une fois dans total_resolues"""
    conn = make_db()
    today = date.today().isoformat()
    for _ in range(3):
        insert_analyse(conn, today, "main.py", [ERREUR_CRITIQUE])
    marquer_resolue(conn, "main.py", ERREUR_CRITIQUE["ligne"], "critique")

    result = get_stats_avec(conn, "semaine")

    assert result.total_erreurs == 0
    assert result.total_resolues == 1


def test_stats_top3_regroupe_malgre_titre_reformule():
    """
    Le LLM reformule le titre d'un scan à l'autre : la même erreur (même
    fichier/ligne/niveau) doit rester UNE entrée du Top 3, pas deux.
    """
    conn = make_db()
    today = date.today().isoformat()
    insert_analyse(conn, today, "app.py", [
        {**ERREUR_CRITIQUE, "fichier": "app.py", "titre": "Injection SQL potentielle"}
    ])
    insert_analyse(conn, today, "app.py", [
        {**ERREUR_CRITIQUE, "fichier": "app.py", "titre": "Injection SQL possible"}
    ])

    result = get_stats_avec(conn, "semaine")

    # Une seule entrée (et non « potentielle » 1× + « possible » 1×), et une
    # seule occurrence puisque les deux scans ont eu lieu le même jour.
    assert len(result.erreurs_recurrentes) == 1
    assert result.erreurs_recurrentes[0].occurrences == 1
    # Libellé affiché = celui de la détection la plus récente
    assert result.erreurs_recurrentes[0].titre == "Injection SQL possible"


def test_stats_top_cours_regroupe_par_pdf():
    """Deux extraits du même PDF comptent pour un seul cours recommandé"""
    conn = make_db()
    today = date.today().isoformat()
    insert_analyse(conn, today, "main.py", [{
        **ERREUR_CRITIQUE,
        "cours": [
            {"titre": "Algorithmie — les variables", "chunk_id": "Algorithmie.pdf__chunk_0"},
            {"titre": "Algorithmie — les boucles",   "chunk_id": "Algorithmie.pdf__chunk_3"},
        ],
    }])

    result = get_stats_avec(conn, "semaine")

    assert len(result.cours_frequents) == 1
    assert result.cours_frequents[0].titre == "Algorithmie"
    assert result.cours_frequents[0].recommandations == 2