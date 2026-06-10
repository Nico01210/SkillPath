from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import import_router, scan_router, rapport_router
from backend.services import sqlite_service

app = FastAPI(title="Coach IA", version="0.1.0")
 
# CORS — autorise le frontend local (port 5500 si Live Server, ou même origine)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre en prod
    allow_methods=["*"],
    allow_headers=["*"],
)
 
 # Fichiers statiques (HTML/CSS/JS du frontend)
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

app.include_router(import_router.router, prefix="/import", tags=["Import"])
app.include_router(scan_router.router, prefix="/scan", tags=["Scan"])
app.include_router(rapport_router.router, prefix="/rapport", tags=["Rapport"])


@app.on_event("startup")
def startup():
    """Initialise la base SQLite au démarrage du serveur."""
    sqlite_service.init_db()
 
@app.get("/health")
def health():
    """Endpoint de vérification — utile pour tester que le serveur tourne."""
    return {"status": "ok", "app": "Coach IA"}