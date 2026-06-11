
from fastapi import APIRouter, UploadFile, File, HTTPException
from backend.models.schemas import ImportResponse
from backend.services import pdf_services, chroma_service

router = APIRouter()


@router.post("/", response_model=ImportResponse)
async def importer_pdf(fichier: UploadFile = File(...)):
    """
    Reçoit un fichier PDF, le découpe en chunks et les stocke dans ChromaDB.
    UploadFile : type FastAPI qui représente un fichier envoyé depuis le navigateur.
    File(...)  : le "..." signifie que le champ est obligatoire.
    """

    if not fichier.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Le fichier doit être un PDF")

    try:
        pdf_bytes = await fichier.read()
        chunks = pdf_services.traiter_pdf(pdf_bytes, fichier.filename)
        nb = chroma_service.stocker_chunks(chunks)
        return ImportResponse(
            filename=fichier.filename,
            chunks=nb,
            message=f"{nb} chunks indexés depuis '{fichier.filename}'"
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur import : {str(e)}")
 