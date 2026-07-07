from fastapi import APIRouter, Query
from backend.models.schemas import StatsResponse
from backend.services import stats_service

router = APIRouter()


@router.get("/dashboard", response_model=StatsResponse)
async def get_dashboard(
    periode: str = Query(default="semaine", pattern="^(semaine|mois)$"),
    offset: int = Query(default=0, ge=0, le=10),
):
    """
    Retourne les stats de progression pour le dashboard.
    ?periode=semaine → 7 derniers jours
    ?periode=mois    → 30 derniers jours

    Query parameter avec validation — si la valeur n'est pas
    "semaine" ou "mois", FastAPI retourne automatiquement une 422.
    """
    return stats_service.get_stats(periode, offset)