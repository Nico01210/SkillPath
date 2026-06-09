from fastapi import APIRouter, UploadFile, File, HTTPException
from backend.models.schemas import ImportResponse
from backend.services import pdf_services as pdf_service, chroma_service
 
router = APIRouter()
 
 
@router.post("/", response_model=ImportResponse)
async def importer_pdf(fichier: UploadFile = File(...)):
    """
    Reçoit un fichier PDF, le découpe en chunks et les stocke dans ChromaDB.
    """
    if not fichier.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Le fichier doit être un PDF")
 
    try:
        # 1. Lit le contenu brut du fichier uploadé
        contenu = await fichier.read()
 
        # 2. Extrait le texte et découpe en chunks
        chunks = pdf_service.traiter_pdf(contenu, fichier.filename)
 
        # 3. Stocke les chunks dans ChromaDB (embed + sauvegarde)
        nb_stockes = chroma_service.stocker_chunks(chunks)
 
        return ImportResponse(
            filename=fichier.filename,
            chunks=nb_stockes,
            message=f"'{fichier.filename}' importé avec succès — {nb_stockes} chunks créés"
        )
 
    except ValueError as e:
        # PDF sans texte extractible (scanné en image par exemple)
        raise HTTPException(status_code=422, detail=str(e))
 
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'import : {str(e)}")