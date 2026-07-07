from fastapi import APIRouter
from backend.models.schemas import Profil
from backend.services import sqlite_service

router = APIRouter()


@router.get("/", response_model=Profil)
async def lire_profil():
    """Profil courant (name, role), ou les valeurs par défaut si jamais défini."""
    return Profil(**sqlite_service.get_profil())


@router.put("/", response_model=Profil)
async def modifier_profil(profil: Profil):
    """Crée ou remplace le profil (app mono-user, upsert sur l'unique ligne)."""
    return Profil(**sqlite_service.set_profil(profil.name, profil.role))
