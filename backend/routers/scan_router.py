from fastapi import APIRouter, UploadFile, File, HTTPException
from backend.models.schemas import ScanResponse, Erreur, CoursLie
from backend.services import llm_service, sqlite_service
from backend.services.upload_utils import read_upload_limited, MAX_CODE_BYTES
import logging


log = logging.getLogger(__name__)
 
router = APIRouter()
 
# Extensions de fichiers de code acceptées
EXTENSIONS_ACCEPTEES = {".py", ".js", ".ts", ".html", ".css", ".java", ".go", ".php", ".cpp", ".c", ".rb"}
 
 
@router.post("/", response_model=ScanResponse)
async def scanner_fichier(fichier: UploadFile = File(...)):
    """
    Reçoit un fichier de code, l'analyse via OpenAI + RAG ChromaDB,
    sauvegarde le résultat dans SQLite et retourne les erreurs détectées.
    """
 
    # Vérification de l'extension
    nom = fichier.filename or ""
    extension = "." + nom.rsplit(".", 1)[-1].lower() if "." in nom else ""
    if extension not in EXTENSIONS_ACCEPTEES:
        liste = ", ".join(sorted(EXTENSIONS_ACCEPTEES))
        raise HTTPException(status_code=400, detail=f"Extension non supportée. Acceptées : {liste}")

    # Lecture bornée — hors du try pour que la 413 ne devienne pas une 500.
    contenu_bytes = await read_upload_limited(fichier, MAX_CODE_BYTES)

    try:
        # Décode le contenu du fichier en texte
        contenu = contenu_bytes.decode("utf-8")
 
        # Analyse via LLM (mock ou OpenAI) + enrichissement RAG
        erreurs = llm_service.analyser_code(contenu, fichier.filename)
 
        # Sauvegarde dans SQLite pour le rapport journalier
        sqlite_service.sauvegarder_analyse(fichier.filename, erreurs)

        nb = len(erreurs)
        return ScanResponse(
            fichier=fichier.filename,
            erreurs=erreurs,
            message=f"{nb} erreur{'s' if nb > 1 else ''} détectée{'s' if nb > 1 else ''}"
        )
 
    except UnicodeDecodeError:
        raise HTTPException(status_code=422, detail="Le fichier doit être en UTF-8")

    except ValueError as e:
        # Analyse IA illisible / tronquée — message explicite plutôt qu'un faux « 0 erreur »
        raise HTTPException(status_code=422, detail=str(e))

    except Exception:
        log.exception("scan failed for %s", fichier.filename)
        raise HTTPException(status_code=500, detail="Erreur interne lors de l'analyse")
 