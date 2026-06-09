from fastapi import APIRouter, UploadFile, File, HTTPException
from backend.models.schemas import ScanResponse, Erreur, CoursLie
 
router = APIRouter()
 
# Extensions de fichiers de code acceptées
EXTENSIONS_ACCEPTEES = {".py", ".js", ".ts", ".html", ".css", ".java"}
 
 
@router.post("/", response_model=ScanResponse)
async def scanner_fichier(fichier: UploadFile = File(...)):
    """
    Reçoit un fichier de code, l'analyse via OpenAI + RAG ChromaDB,
    sauvegarde le résultat dans SQLite et retourne les erreurs détectées.
    """
 
    # Vérification de l'extension
    extension = "." + fichier.filename.split(".")[-1]
    if extension not in EXTENSIONS_ACCEPTEES:
        raise HTTPException(
            status_code=400,
            detail=f"Extension non supportée. Acceptées : {EXTENSIONS_ACCEPTEES}"
        )

    # Données fictives pour tester que l'endpoint répond
    erreurs_mock = [
        Erreur(
            niveau="critique",
            titre="Fonction trop longue",
            fichier=fichier.filename,
            ligne=42,
            description="La fonction dépasse 20 lignes. Règle : une fonction = une responsabilité.",
            extrait="def process_data(df):\n    # trop de logique ici...",
            cours=[
                CoursLie(titre="Chapitre 3 — Fonctions et SRP", chunk_id="mock-001")
            ]
        )
    ]
 
    return ScanResponse(
        fichier=fichier.filename,
        erreurs=erreurs_mock,
        message=f"[MOCK] 1 erreur fictive — service LLM pas encore branché"
    )