from datetime import date
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import FileResponse
from backend.models.schemas import RapportResponse
from backend.services import rapport_service, sqlite_service

router = APIRouter()


def _parse_date(date_str: str | None) -> date:
    """Convertit ?date=AAAA-MM-JJ en date, ou renvoie aujourd'hui si absent."""
    if not date_str:
        return date.today()
    try:
        return date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Date invalide (format attendu : AAAA-MM-JJ)")


@router.get("/", response_model=RapportResponse)
async def generer_rapport(date: str | None = Query(default=None)):
    """Rapport d'une journée. Sans ?date=, renvoie aujourd'hui."""
    return rapport_service.get_rapport(_parse_date(date))


@router.get("/dates")
async def lister_dates():
    """Liste des journées disposant d'au moins une analyse (plus récentes d'abord)."""
    return {"dates": sqlite_service.get_dates_analysees()}


@router.get("/hier", response_model=RapportResponse)
async def rapport_hier():
    return rapport_service.get_rapport_hier()


@router.get("/export")
async def exporter_rapport_html(date: str | None = Query(default=None)):
    jour = _parse_date(date)
    rapport = rapport_service.get_rapport(jour)
    html = rapport_service.generer_html(rapport)
    chemin = rapport_service.sauvegarder_html(html, jour)
    return FileResponse(
        path=chemin,
        media_type="text/html",
        filename=f"SkillPath_rapport_{rapport.date}.html"
    )
