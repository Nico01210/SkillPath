from datetime import date, timedelta
from collections import Counter
import json

from backend.services import sqlite_service
from backend.models.schemas import (
    StatsResponse, PointCourbe, ErreurRecurrente, CoursFrequent, signature_erreur
)


def _nom_cours(cours: dict) -> str:
    """
    Nom du cours (le PDF) auquel appartient un chunk recommandé.

    Le titre d'un CoursLie décrit un extrait précis, pas le cours entier : deux
    extraits du même PDF donnent deux titres différents. Or le panneau s'appelle
    « Top 3 cours recommandés » — on regroupe donc par PDF, que l'on retrouve
    depuis le chunk_id (« mon_cours.pdf__chunk_3 »).
    """
    chunk_id = cours.get("chunk_id") or ""
    source = chunk_id.rsplit("__chunk_", 1)[0] if "__chunk_" in chunk_id else ""
    if not source:
        return cours.get("titre", "Cours inconnu")
    return source[:-4] if source.lower().endswith(".pdf") else source


def get_stats(periode: str = "semaine", offset: int = 0) -> StatsResponse:
    """
    Calcule les stats de progression sur 7 ou 30 jours.
    periode = "semaine" → 7 jours
    periode = "mois"    → 30 jours
    """
    nb_jours = 7 if periode == "semaine" else 30

    date_fin   = date.today() - timedelta(days=nb_jours * offset)
    date_debut = date_fin - timedelta(days=nb_jours - 1)
 
    conn = sqlite_service.get_connexion()
    rows = conn.execute(
        "SELECT * FROM analyses WHERE date >= ? AND date <= ? ORDER BY date ASC",
        (date_debut.isoformat(), date_fin.isoformat())
    ).fetchall()
 
    # Erreurs cochées « résolues » : elles sortent des stats, sinon la
    # progression ne bouge jamais quand on corrige quelque chose.
    resolues = set(sqlite_service.get_resolutions())

    # Parse toutes les erreurs
    # Clé (jour, signature) → erreur : re-scanner le même fichier plusieurs fois
    # dans la journée ne compte qu'une fois. Sinon un jour où l'on re-scanne
    # beaucoup paraissait pire qu'un autre, et la courbe annonçait 3 erreurs là
    # où le rapport du même jour en affichait 1.
    # dict : position de la 1re détection, contenu de la plus récente.
    par_jour_et_signature: dict[tuple[str, str], dict] = {}
    fichiers_vus = set()
    signatures_resolues = set()

    for row in rows:
        fichiers_vus.add(row["fichier"])
        erreurs = json.loads(row["erreurs"])
        for e in erreurs:
            # Recalculée et non relue depuis le JSON : les analyses enregistrées
            # avant le changement de formule portent une signature obsolète.
            e["_signature"] = signature_erreur(
                e.get("fichier") or row["fichier"], e["ligne"], e["niveau"]
            )
            e["_date"] = row["date"]  # on garde la date pour la courbe
            if e["_signature"] in resolues:
                signatures_resolues.add(e["_signature"])
                continue
            par_jour_et_signature[(e["_date"], e["_signature"])] = e

    # Une entrée = une erreur distincte détectée un jour donné.
    # total_erreurs reste donc égal à la somme de la courbe.
    toutes_erreurs = list(par_jour_et_signature.values())

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
    # Regroupées par signature et non par titre : le titre est reformulé par le
    # LLM à chaque scan, ce qui faisait apparaître deux fois la même erreur
    # (« Injection SQL potentielle » 2× + « Injection SQL possible » 1×).
    # « occurrences » = nombre de JOURS où l'erreur a été détectée (les re-scans
    # d'une même journée sont déjà dédupliqués) : une erreur récurrente est une
    # erreur qui revient jour après jour, pas une qu'on a re-scannée dix fois.
    compteur_erreurs = Counter(e["_signature"] for e in toutes_erreurs)

    # Libellé affiché : le titre de la détection la plus récente.
    # Gravité : si l'erreur a déjà été vue « critique », elle reste « critique ».
    titre_par_signature = {}
    niveau_par_signature = {}
    for e in toutes_erreurs:
        sig = e["_signature"]
        titre_par_signature[sig] = e["titre"]
        if niveau_par_signature.get(sig) != "critique":
            niveau_par_signature[sig] = e["niveau"]

    # Les erreurs critiques passent toujours avant les avertissements,
    # peu importe le nombre d'occurrences ; à gravité égale, par fréquence
    classement = sorted(
        compteur_erreurs.items(),
        key=lambda item: (niveau_par_signature[item[0]] != "critique", -item[1])
    )

    erreurs_recurrentes = [
        ErreurRecurrente(
            titre=titre_par_signature[sig],
            occurrences=count,
            niveau=niveau_par_signature[sig],
        )
        for sig, count in classement[:3]
    ]

    # ── Top 3 cours les plus recommandés ─────────────────
    tous_cours = []
    for e in toutes_erreurs:
        for c in e.get("cours", []):
            tous_cours.append(_nom_cours(c))

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
        total_resolues=len(signatures_resolues),
        courbe=courbe,
        erreurs_recurrentes=erreurs_recurrentes,
        cours_frequents=cours_frequents
    )