import sqlite3
import json
import threading
from datetime import date, datetime
from backend.config import settings
from backend.models.schemas import Erreur
from datetime import timedelta

# Les endpoints FastAPI synchrones tournent dans un threadpool : partager une
# seule connexion SQLite entre threads provoque des « database is locked » et des
# corruptions d'état. On donne donc une connexion propre à chaque thread.
_local = threading.local()


def get_connexion():
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(settings.sqlite_db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # WAL : lectures et écritures concurrentes ne se bloquent plus mutuellement.
        conn.execute("PRAGMA journal_mode=WAL")
        _local.conn = conn
    return conn


def init_db():
    """
    Crée la table 'analyses' si elle n'existe pas.
    À appeler au démarrage de l'app dans main.py.
    """
    conn = get_connexion()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            date        TEXT NOT NULL,
            fichier     TEXT NOT NULL,
            erreurs     TEXT NOT NULL,  -- JSON sérialisé
            created_at  TEXT NOT NULL
        )
    """)
    conn.commit()


def sauvegarder_analyse(fichier: str, erreurs: list[Erreur]):
    """
    Sauvegarde le résultat d'un scan dans SQLite.
    Les erreurs sont sérialisées en JSON — SQLite ne stocke pas de listes nativement.
    """
    conn = get_connexion()

    # Convertit les objets Pydantic en dicts sérialisables
    erreurs_json = json.dumps(
        [e.model_dump() for e in erreurs],
        ensure_ascii=False
    )

    conn.execute(
        "INSERT INTO analyses (date, fichier, erreurs, created_at) VALUES (?, ?, ?, ?)",
        (
            date.today().isoformat(),       # "2026-06-09"
            fichier,
            erreurs_json,
            datetime.now().isoformat()      # "2026-06-09T14:32:00"
        )
    )
    conn.commit()


def get_analyses_du_jour() -> list[dict]:
    """
    Retourne toutes les analyses d'aujourd'hui.
    Utilisé par rapport_service pour construire le rapport journalier.
    """
    conn = get_connexion()
    rows = conn.execute(
        "SELECT * FROM analyses WHERE date = ?",
        (date.today().isoformat(),)
    ).fetchall()

    analyses = []
    for row in rows:
        analyses.append({
            "id": row["id"],
            "fichier": row["fichier"],
            "erreurs": json.loads(row["erreurs"]),
            "created_at": row["created_at"]
        })

    return analyses


def compter_analyses_du_jour() -> int:
    """Retourne le nombre de fichiers analysés aujourd'hui."""
    conn = get_connexion()
    count = conn.execute(
        "SELECT COUNT(*) FROM analyses WHERE date = ?",
        (date.today().isoformat(),)
    ).fetchone()[0]
    return count

def get_analyses_hier() -> list[dict]:
    """Retourne les analyses du jour précédent."""
    hier = (date.today() - timedelta(days=1)).isoformat()
    conn = get_connexion()
    rows = conn.execute(
        "SELECT * FROM analyses WHERE date = ?", (hier,)
    ).fetchall()

    return [
        {
            "id": row["id"],
            "fichier": row["fichier"],
            "erreurs": json.loads(row["erreurs"]),
            "created_at": row["created_at"]
        }
        for row in rows
    ]