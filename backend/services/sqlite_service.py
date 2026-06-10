import sqlite3
import json
from datetime import date, datetime
from backend.config import settings
from backend.models.schemas import Erreur


def get_connexion() -> sqlite3.Connection:
    """
    Retourne une connexion SQLite.
    check_same_thread=False nécessaire pour FastAPI qui utilise plusieurs threads.
    """
    conn = sqlite3.connect(settings.sqlite_db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # retourne des dicts au lieu de tuples
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
    conn.close()


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
    conn.close()


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
    conn.close()

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
    conn.close()
    return count