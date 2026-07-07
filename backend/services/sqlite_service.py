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
    # Erreurs marquées « résolues » par l'utilisateur, identifiées par la
    # signature stable de l'erreur (voir Erreur.signature).
    conn.execute("""
        CREATE TABLE IF NOT EXISTS resolutions (
            signature   TEXT PRIMARY KEY,
            resolved_at TEXT NOT NULL
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


def get_analyses_par_date(jour: date) -> list[dict]:
    """
    Retourne toutes les analyses d'une date donnée.
    Brique de base pour le rapport du jour, d'hier ou de n'importe quelle
    journée passée (historique).
    """
    conn = get_connexion()
    rows = conn.execute(
        "SELECT * FROM analyses WHERE date = ?",
        (jour.isoformat(),)
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


def get_resolutions() -> list[str]:
    """Retourne les signatures des erreurs marquées comme résolues."""
    conn = get_connexion()
    rows = conn.execute("SELECT signature FROM resolutions").fetchall()
    return [row["signature"] for row in rows]


def marquer_resolue(signature: str) -> None:
    """Marque une erreur (par sa signature) comme résolue. Idempotent."""
    conn = get_connexion()
    conn.execute(
        "INSERT OR IGNORE INTO resolutions (signature, resolved_at) VALUES (?, ?)",
        (signature, datetime.now().isoformat())
    )
    conn.commit()


def rouvrir_erreur(signature: str) -> None:
    """Annule la résolution d'une erreur. Idempotent."""
    conn = get_connexion()
    conn.execute("DELETE FROM resolutions WHERE signature = ?", (signature,))
    conn.commit()


def get_dates_analysees() -> list[str]:
    """Retourne la liste des dates ayant au moins une analyse (plus récentes d'abord)."""
    conn = get_connexion()
    rows = conn.execute(
        "SELECT DISTINCT date FROM analyses ORDER BY date DESC"
    ).fetchall()
    return [row["date"] for row in rows]


def get_analyses_du_jour() -> list[dict]:
    """Analyses d'aujourd'hui — raccourci sur get_analyses_par_date."""
    return get_analyses_par_date(date.today())


def get_analyses_hier() -> list[dict]:
    """Analyses du jour précédent — raccourci sur get_analyses_par_date."""
    return get_analyses_par_date(date.today() - timedelta(days=1))