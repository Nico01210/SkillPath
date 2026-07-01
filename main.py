from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from fastapi.templating import Jinja2Templates

from backend.routers import import_router, scan_router, rapport_router, stats_router
from backend.services import sqlite_service

app = FastAPI(title="SkillPath", version="0.1.0")
templates = Jinja2Templates(directory="frontend/templates")
 
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
app.include_router(stats_router.router, prefix="/stats", tags=["Stats"])

@app.on_event("startup")
def startup():
    """Initialise la base SQLite au démarrage du serveur."""
    sqlite_service.init_db()
 
@app.get("/health")
def health():
    """Endpoint de vérification — utile pour tester que le serveur tourne."""
    return {"status": "ok", "app": "SkillPath"}

# ── Routes pages frontend ─────────────────────────
 
@app.get("/")
def index(request: Request):
    return templates.TemplateResponse("import.html", {"request": request, "active_page": "import"})
 
@app.get("/import-cours")
def page_import(request: Request):
    return templates.TemplateResponse("import.html", {"request": request, "active_page": "import"})
 
@app.get("/scan-code")
def page_scan(request: Request):
    return templates.TemplateResponse("scan.html", {"request": request, "active_page": "scan"})
 
@app.get("/rapport-jour")
def page_rapport(request: Request):
    return templates.TemplateResponse("rapport.html", {"request": request, "active_page": "rapport"})
 
@app.get("/dashboard")
def page_dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request, "active_page": "dashboard"})