from fastapi import APIRouter
from datetime import date
from backend.models.schemas import RapportResponse, StatsRapport, Erreur, CoursLie
 
router = APIRouter()
 
 
@router.get("/", response_model=RapportResponse)
async def generer_rapport():
    """
    Agrège toutes les analyses SQLite du jour et retourne le rapport complet.
    Le frontend utilise ces données pour afficher et exporter le HTML.
    """
 
    # Données fictives pour tester que l'endpoint répond
    erreurs_mock = [
        Erreur(
            niveau="critique",
            titre="Fonction trop longue",
            fichier="main.py",
            ligne=42,
            description="La fonction dépasse 20 lignes.",
            extrait="def process_data(df):\n    ...",
            cours=[
                CoursLie(titre="Chapitre 3 — Fonctions et SRP", chunk_id="mock-001"),
                CoursLie(titre="Chapitre 5 — Clean Code", chunk_id="mock-002"),
            ]
        ),
        Erreur(
            niveau="avertissement",
            titre="Pas de gestion d'erreur",
            fichier="api.py",
            ligne=55,
            description="Appel réseau sans try/except.",
            extrait="response = requests.get(url)",
            cours=[
                CoursLie(titre="Chapitre 7 — Exceptions", chunk_id="mock-003")
            ]
        )
    ]
 
    return RapportResponse(
        date=date.today(),
        stats=StatsRapport(
            critiques=1,
            avertissements=1,
            fichiers_analyses=2,
            cours_a_relire=3
        ),
        erreurs=erreurs_mock
    )
 
 
@router.get("/export")
async def exporter_rapport_html():
    """
    Génère et retourne le rapport du jour sous forme de fichier HTML téléchargeable.
    response_class=None pour l'instant — on branchera FileResponse semaine 2.
    """
 
 
    return {"message": "[MOCK] Export HTML pas encore branché"}