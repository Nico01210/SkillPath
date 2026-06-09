from pydantic import BaseModel
from datetime import date


# ─── IMPORT ───────────────────────────────────────────────
# Le frontend envoie un PDF, FastAPI répond avec ça :

class ImportResponse(BaseModel):
    filename: str       # nom du fichier importé
    chunks: int         # nombre de morceaux créés (ex: 12)
    message: str        # confirmation lisible


# ─── SCAN ─────────────────────────────────────────────────
# Une erreur détectée dans le code

class CoursLie(BaseModel):
    titre: str          # ex: "Chapitre 3 — Fonctions et SRP"
    chunk_id: str       # identifiant du morceau dans ChromaDB

class Erreur(BaseModel):
    niveau: str         # "critique" ou "avertissement"
    titre: str          # ex: "Fonction trop longue"
    fichier: str        # ex: "main.py"
    ligne: int          # numéro de ligne
    description: str    # explication de l'erreur
    extrait: str        # bout de code fautif
    cours: list[CoursLie]  # cours à relire (vient du RAG)

# Ce que retourne POST /scan
class ScanResponse(BaseModel):
    fichier: str
    erreurs: list[Erreur]
    message: str        # ex: "3 erreurs détectées"


# ─── RAPPORT ──────────────────────────────────────────────
# Agrégation de toutes les analyses de la journée

class StatsRapport(BaseModel):
    critiques: int
    avertissements: int
    fichiers_analyses: int
    cours_a_relire: int

# Ce que retourne GET /rapport
class RapportResponse(BaseModel):
    date: date
    stats: StatsRapport
    erreurs: list[Erreur]   # toutes les erreurs du jour