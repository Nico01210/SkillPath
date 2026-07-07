
import os
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException
from backend.models.schemas import ImportResponse
from backend.services import pdf_service, chroma_service
from backend.config import settings

log = logging.getLogger(__name__)


def _safe_filename(name: str) -> str:
    base = os.path.basename(name or "")
    if base in ("", ".", ".."):
        raise HTTPException(status_code=400, detail="Nom de fichier invalide")
    return base

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
        # 1. Lit le contenu brut du fichier uploadé
        contenu = await fichier.read()
 
        # 2. Sauvegarde une copie du PDF dans uploads/
        os.makedirs(settings.uploads_path, exist_ok=True)
        chemin_sauvegarde = os.path.join(settings.uploads_path, _safe_filename(fichier.filename))
        with open(chemin_sauvegarde, "wb") as f:
            f.write(contenu)

        try:
            # 3. Extrait le texte et découpe en chunks
            resultat = pdf_service.traiter_pdf(contenu, fichier.filename)

            # 4. Stocke les chunks dans ChromaDB (embed + sauvegarde)
            nb_stockes = chroma_service.stocker_chunks(resultat["chunks"])
        except Exception:
            # Le fichier ne doit pas rester orphelin si l'indexation échoue
            if os.path.exists(chemin_sauvegarde):
                os.remove(chemin_sauvegarde)
            raise

        return ImportResponse(
            filename=fichier.filename,
            chunks=nb_stockes,
            pages=resultat["pages"],
            message=f"'{fichier.filename}' importé avec succès — {nb_stockes} chunks créés"
        )

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    except Exception:
        log.exception("import failed for %s", fichier.filename)
        raise HTTPException(status_code=500, detail="Erreur interne lors de l'import")
 
 
@router.get("/liste")
async def lister_cours():
    """
    Retourne la liste des PDFs sauvegardés dans data/uploads/.
    Utile pour savoir quels cours sont chargés dans ChromaDB,
    et pour les réimporter si ChromaDB est vidé.
    """
    os.makedirs(settings.uploads_path, exist_ok=True)
 
    fichiers = [
        f for f in os.listdir(settings.uploads_path)
        if f.endswith(".pdf")
    ]
 
    return {
        "total": len(fichiers),
        "cours": sorted(fichiers)
    }
 
 
@router.get("/chunk")
async def get_chunk(chunk_id: str):
    """
    Retourne le texte d'un chunk de cours à partir de son chunk_id.
    Alimente la modale « Cours à relire » quand on clique sur un tag.
    """
    chunk = chroma_service.get_chunk(chunk_id)
    if chunk is None:
        raise HTTPException(
            status_code=404,
            detail="Extrait introuvable — le cours a peut-être été supprimé de l'index.",
        )
    return chunk


@router.delete("/{nom_fichier}")
async def supprimer_cours(nom_fichier: str):
    """
    Supprime un PDF de uploads/ ainsi que ses chunks dans ChromaDB.
    """
    if os.path.basename(nom_fichier) != nom_fichier:
        raise HTTPException(status_code=400, detail="Nom de fichier invalide")

    chemin = os.path.join(settings.uploads_path, nom_fichier)

    if not os.path.isfile(chemin):
        raise HTTPException(status_code=404, detail=f"'{nom_fichier}' introuvable")

    # Supprime d'abord les chunks : si ça échoue, le fichier reste et l'opération
    # peut être retentée sans laisser de vecteurs orphelins dans ChromaDB.
    chroma_service.supprimer_chunks(nom_fichier)
    os.remove(chemin)

    return {"message": f"'{nom_fichier}' supprimé avec succès"}


@router.post("/reimporter-tout")
async def reimporter_tout():
    """
    Relit tous les PDFs du dossier uploads/ et les réimporte dans ChromaDB.
    Utile si ChromaDB est corrompu ou vidé accidentellement.
    """
    os.makedirs(settings.uploads_path, exist_ok=True)
 
    fichiers = [
        f for f in os.listdir(settings.uploads_path)
        if f.endswith(".pdf")
    ]
 
    if not fichiers:
        raise HTTPException(
            status_code=404,
            detail="Aucun PDF trouvé dans uploads/. Importez d'abord des cours."
        )
 
    resultats = []
    for nom_fichier in fichiers:
        try:
            chemin = os.path.join(settings.uploads_path, nom_fichier)
            with open(chemin, "rb") as f:
                contenu = f.read()
 
            resultat = pdf_service.traiter_pdf(contenu, nom_fichier)
            nb = chroma_service.stocker_chunks(resultat["chunks"])
            resultats.append({"fichier": nom_fichier, "chunks": nb, "statut": "ok"})
 
        except Exception as e:
            resultats.append({"fichier": nom_fichier, "chunks": 0, "statut": f"erreur: {str(e)}"})
 
    total_chunks = sum(r["chunks"] for r in resultats)
    return {
        "total_fichiers": len(resultats),
        "total_chunks": total_chunks,
        "detail": resultats
    }