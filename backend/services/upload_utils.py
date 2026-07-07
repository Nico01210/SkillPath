from fastapi import UploadFile, HTTPException

# Limites de taille côté serveur (le check client est contournable).
MAX_PDF_BYTES = 10 * 1024 * 1024   # 10 Mo — cours PDF
MAX_CODE_BYTES = 1 * 1024 * 1024   # 1 Mo — fichier de code

_READ_CHUNK = 1024 * 1024  # lit par blocs de 1 Mo


async def read_upload_limited(fichier: UploadFile, max_bytes: int) -> bytes:
    """
    Lit un fichier uploadé en s'arrêtant dès que la limite est dépassée,
    pour ne jamais charger un fichier géant entièrement en mémoire.
    Lève une 413 (Payload Too Large) si le fichier est trop gros.
    """
    morceaux = []
    total = 0
    while True:
        bloc = await fichier.read(_READ_CHUNK)
        if not bloc:
            break
        total += len(bloc)
        if total > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"Fichier trop volumineux (max {max_bytes // (1024 * 1024)} Mo).",
            )
        morceaux.append(bloc)
    return b"".join(morceaux)
