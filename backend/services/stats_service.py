from datetime import date, timedelta
from collections import Counter
import json

from backend.services import sqlite_service
from backend.models.schemas import (
    StatsResponse, PointCourbe, ErreurRecurrente, CoursFrequent
)


def get_stats(periode: str = "semaine") -> StatsResponse:
    """
    Calcule les stats de progression sur 7 ou 30 jours.
    periode = "semaine" → 7 jours
    periode = "mois"    → 30 jours
    """
    nb_jours = 7 if periode == "semaine" else 30
    date_fin = date.today()
    date_debut = date_fin - timedelta(days=nb_jours - 1)
 
    conn = sqlite_service.get_connexion()
    rows = conn.execute(
        "SELECT * FROM analyses WHERE date >= ? AND date <= ? ORDER BY date ASC",
        (date_debut.isoformat(), date_fin.isoformat())
    ).fetchall()
 
    # Parse toutes les erreurs
    toutes_erreurs = []
    fichiers_vus = set()
 
    for row in rows:
        fichiers_vus.add(row["fichier"])
        erreurs = json.loads(row["erreurs"])
        for e in erreurs:
            e["_date"] = row["date"]  # on garde la date pour la courbe
            toutes_erreurs.append(e)
 
    # ── Courbe jour par jour ──────────────────────────────
    courbe = []
    for i in range(nb_jours):
        jour = (date_debut + timedelta(days=i)).isoformat()
        erreurs_jour = [e for e in toutes_erreurs if e["_date"] == jour]
        courbe.append(PointCourbe(
            date=jour,
            total_erreurs=len(erreurs_jour),
            critiques=sum(1 for e in erreurs_jour if e["niveau"] == "critique"),
            avertissements=sum(1 for e in erreurs_jour if e["niveau"] == "avertissement")
        ))
 
    # ── Top 3 erreurs récurrentes ─────────────────────────
    # Counter compte les occurrences de chaque titre d'erreur
    compteur_erreurs = Counter(e["titre"] for e in toutes_erreurs)

    # Si un titre a déjà été vu en "critique", il reste "critique"
    niveau_par_titre = {}
    for e in toutes_erreurs:
        if niveau_par_titre.get(e["titre"]) != "critique":
            niveau_par_titre[e["titre"]] = e["niveau"]

    # Les erreurs critiques passent toujours avant les avertissements,
    # peu importe le nombre d'occurrences ; à gravité égale, par fréquence
    classement = sorted(
        compteur_erreurs.items(),
        key=lambda item: (niveau_par_titre[item[0]] != "critique", -item[1])
    )

    erreurs_recurrentes = [
        ErreurRecurrente(titre=titre, occurrences=count, niveau=niveau_par_titre[titre])
        for titre, count in classement[:3]
    ]
 
    # ── Top 3 cours les plus recommandés ─────────────────
    tous_cours = []
    for e in toutes_erreurs:
        for c in e.get("cours", []):
            tous_cours.append(c["titre"])
 
    compteur_cours = Counter(tous_cours)
    cours_frequents = [
        CoursFrequent(titre=titre, recommandations=count)
        for titre, count in compteur_cours.most_common(3)
    ]
 
    return StatsResponse(
        periode=periode,
        date_debut=date_debut.isoformat(),
        date_fin=date_fin.isoformat(),
        total_fichiers=len(fichiers_vus),
        total_erreurs=len(toutes_erreurs),
        courbe=courbe,
        erreurs_recurrentes=erreurs_recurrentes,
        cours_frequents=cours_frequents
    )