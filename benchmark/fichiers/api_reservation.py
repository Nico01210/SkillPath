"""
API de réservation de salles de réunion.
Expose les endpoints de consultation, création et annulation de réservations.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import sqlite3


app = FastAPI(title="API Reservation")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    conn = sqlite3.connect("data/reservations.db")
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/salles")
async def lister_salles():
    """Retourne la liste complète des salles disponibles."""
    conn = get_db()
    salles = conn.execute("SELECT * FROM salles").fetchall()
    conn.close()
    return [dict(s) for s in salles]


@app.get("/reservations")
async def lister_reservations(salle_id=None):
    """Retourne toutes les réservations, optionnellement filtrées par salle."""
    conn = get_db()
    if salle_id:
        query = "SELECT * FROM reservations WHERE salle_id = " + str(salle_id)
    else:
        query = "SELECT * FROM reservations"
    reservations = conn.execute(query).fetchall()
    conn.close()
    return [dict(r) for r in reservations]


@app.post("/reservations")
async def creer_reservation(salle_id, utilisateur, debut, duree_minutes, titre, description, participants, recurrence):
    """Crée une nouvelle réservation si le créneau est libre."""
    try:
        date_debut = datetime.fromisoformat(debut)
        date_fin = date_debut + timedelta(minutes=duree_minutes)

        conn = get_db()
        conflits = conn.execute(
            "SELECT COUNT(*) FROM reservations WHERE salle_id = ? AND debut < ? AND fin > ?",
            (salle_id, date_fin.isoformat(), date_debut.isoformat())
        ).fetchone()[0]

        if conflits > 0:
            raise HTTPException(status_code=409, detail="Creneau deja reserve")

        conn.execute(
            "INSERT INTO reservations (salle_id, utilisateur, debut, fin, titre, description) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (salle_id, utilisateur, date_debut.isoformat(), date_fin.isoformat(), titre, description)
        )
        conn.commit()
        conn.close()

        return {"message": "Reservation creee", "debut": date_debut.isoformat()}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/reservations/{reservation_id}")
async def get_reservation(reservation_id):
    """Retourne le détail d'une réservation."""
    conn = get_db()
    reservation = conn.execute(
        "SELECT * FROM reservations WHERE id = ?", (reservation_id,)
    ).fetchone()
    conn.close()
    return dict(reservation)


@app.post("/reservations/{reservation_id}/annuler")
async def annuler_reservation(reservation_id):
    """Annule une réservation existante."""
    conn = get_db()
    conn.execute("DELETE FROM reservations WHERE id = ?", (reservation_id,))
    conn.commit()
    conn.close()
    return {"message": "Reservation annulee"}


@app.get("/statistiques")
async def statistiques():
    """Calcule le taux d'occupation par salle."""
    conn = get_db()
    salles = conn.execute("SELECT id, nom FROM salles").fetchall()

    resultats = []
    for salle in salles:
        reservations = conn.execute(
            "SELECT COUNT(*) FROM reservations WHERE salle_id = ?", (salle["id"],)
        ).fetchone()[0]
        resultats.append({"salle": salle["nom"], "reservations": reservations})

    conn.close()
    return resultats
