from fastapi import APIRouter
from backend.services import sqlite_service

router = APIRouter()


@router.get("/")
async def lister_resolutions():
    """Signatures des erreurs actuellement marquées comme résolues."""
    return {"resolues": sqlite_service.get_resolutions()}


@router.put("/{signature}")
async def resoudre(signature: str):
    """Marque une erreur comme résolue (idempotent)."""
    sqlite_service.marquer_resolue(signature)
    return {"signature": signature, "resolue": True}


@router.delete("/{signature}")
async def rouvrir(signature: str):
    """Rouvre une erreur précédemment résolue (idempotent)."""
    sqlite_service.rouvrir_erreur(signature)
    return {"signature": signature, "resolue": False}
