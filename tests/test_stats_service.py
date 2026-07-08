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
    """Crée une DB SQLite en mémoire avec la table analyses."""
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
    conn.commit()
    return conn


def insert_analyse(conn, date_str: str, fichier: str, erreurs: list):
    conn.execute(
        "INSERT INTO analyses (date, fichier, erreurs, created_at) VALUES (?, ?, ?, ?)",
        (date_str, fichier, json.dumps(erreurs), f"{date_str}T10:00:00")
    )
    conn.commit()


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
    """Top 3 erreurs récurrentes triées par occurrences"""
    conn = make_db()
    today = date.today().isoformat()
    # Insère 3 fois la même erreur critique
    for _ in range(3):
        insert_analyse(conn, today, "main.py", [ERREUR_CRITIQUE])

    with patch("backend.services.sqlite_service.get_connexion", return_value=conn):
        import backend.services.stats_service as ss
        from importlib import reload
        reload(ss)
        result = ss.get_stats("semaine")

    assert len(result.erreurs_recurrentes) >= 1
    assert result.erreurs_recurrentes[0].occurrences == 3