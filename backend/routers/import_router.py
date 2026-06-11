
from fastapi import APIRouter, UploadFile, File, HTTPException
from backend.models.schemas import ImportResponse
 
router = APIRouter()
 
 
@router.post("/", response_model=ImportResponse)
async def importer_pdf(fichier: UploadFile = File(...)):
    """
    Reçoit un fichier PDF, le découpe en chunks et les stocke dans ChromaDB.
    UploadFile : type FastAPI qui représente un fichier envoyé depuis le navigateur.
    File(...)  : le "..." signifie que le champ est obligatoire.
    """
 
    # Vérification du type de fichier
    if not fichier.filename.endswith(".pdf"):
        # HTTPException : façon FastAPI de retourner une erreur HTTP propre
        raise HTTPException(status_code=400, detail="Le fichier doit être un PDF")
 
 
    # Données fictives pour tester que l'endpoint répond
    return ImportResponse(
        filename=fichier.filename,
        chunks=0,
        message=f"[MOCK] {fichier.filename} reçu — service PDF pas encore branché"
    )
 