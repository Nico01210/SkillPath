from fastapi import APIRouter
from fastapi.responses import FileResponse
from backend.models.schemas import RapportResponse
from backend.services import rapport_service

router = APIRouter()


@router.get("/", response_model=RapportResponse)
async def generer_rapport():
    return rapport_service.get_rapport_du_jour()


@router.get("/export")
async def exporter_rapport_html():
    rapport = rapport_service.get_rapport_du_jour()
    html = rapport_service.generer_html(rapport)
    chemin = rapport_service.sauvegarder_html(html)
    return FileResponse(
        path=chemin,
        media_type="text/html",
        filename=f"SkillPath_rapport_{rapport.date}.html"
    )

@router.get("/hier", response_model=RapportResponse)
async def rapport_hier():
    return rapport_service.get_rapport_hier()