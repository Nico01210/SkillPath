from fastapi import APIRouter, UploadFile, File, HTTPException
from backend.models.schemas import ScanResponse, Erreur, CoursLie
from backend.services import llm_service

 
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

    try:
        # Lit le contenu du fichier en texte
        contenu_bytes = await fichier.read()
        contenu = contenu_bytes.decode("utf-8")
 
        # Analyse via LLM (mock ou OpenAI) + enrichissement RAG
        erreurs = llm_service.analyser_code(contenu, fichier.filename)
 
        nb = len(erreurs)
        return ScanResponse(
            fichier=fichier.filename,
            erreurs=erreurs,
            message=f"{nb} erreur{'s' if nb > 1 else ''} détectée{'s' if nb > 1 else ''}"
        )
 
    except UnicodeDecodeError:
        raise HTTPException(status_code=422, detail="Le fichier doit être en UTF-8")
 
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'analyse : {str(e)}")
 