import fitz  # PyMuPDF — fitz est le nom du module interne
from pathlib import Path
 
 
# Taille d'un chunk en nombre de mots.
#
# 500 mots (≈ 1 page) semblait « assez de contexte », mais un cours entier
# tenait alors en 2 ou 3 vecteurs : chaque vecteur moyennait toutes les notions
# du PDF, les scores de similarité s'écrasaient tous entre 0,25 et 0,50 et le
# même chunk fourre-tout ressortait premier sur des erreurs sans rapport.
# 180 mots ≈ une notion — c'est la granularité qu'on veut afficher dans
# « Cours à relire ».
CHUNK_SIZE = 180
CHUNK_OVERLAP = 40  # mots partagés entre deux chunks consécutifs
                    # évite de couper une explication en plein milieu
 
 
def extraire_texte(pdf_bytes: bytes) -> tuple[str, int]:
    """
    Lit un PDF depuis ses bytes bruts et retourne (texte, nombre_de_pages).
    On reçoit des bytes car le fichier vient d'un upload FastAPI.
    """
    # fitz.open avec stream= lit depuis la mémoire, pas depuis un fichier.
    # Un fichier corrompu ou simplement renommé « .pdf » fait lever PyMuPDF :
    # on le traduit en ValueError, que le routeur présente en 422 explicite
    # plutôt qu'en 500 « Erreur interne » qui ressemble à un plantage.
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        raise ValueError(
            "Fichier PDF illisible ou corrompu — vérifie qu'il s'ouvre "
            "correctement dans un lecteur PDF."
        ) from exc

    nb_pages = len(doc)
 
    texte_complet = []
    for page in doc:
        texte_complet.append(page.get_text())
 
    doc.close()
    return "\n".join(texte_complet), nb_pages
 
 
def decouper_en_chunks(texte: str, source: str) -> list[dict]:
    """
    Découpe un texte en morceaux de CHUNK_SIZE mots avec chevauchement.
    Retourne une liste de dicts prêts à être stockés dans ChromaDB.
 
    Exemple de chunk retourné :
    {
        "text": "En Python, une fonction ne doit pas...",
        "source": "cours_python.pdf",
        "chunk_index": 0
    }
    """
    mots = texte.split()
    chunks = []
    index = 0
    position = 0
 
    while position < len(mots):
        # Prend CHUNK_SIZE mots à partir de la position courante
        fin = min(position + CHUNK_SIZE, len(mots))
        chunk_mots = mots[position:fin]
        chunk_texte = " ".join(chunk_mots)
 
        # Ignore les chunks trop courts (fin de document)
        if len(chunk_mots) > 20:
            chunks.append({
                "text": chunk_texte,
                "source": source,
                "chunk_index": index
            })
            index += 1
 
        # Avance en tenant compte du chevauchement
        # ex: position 0 → next position 450 (500 - 50)
        position += CHUNK_SIZE - CHUNK_OVERLAP
 
    return chunks
 
 
def traiter_pdf(pdf_bytes: bytes, filename: str) -> dict:
    """
    Fonction principale appelée par import_router.
    Lit le PDF et retourne {"chunks": [...], "pages": int} prêt pour ChromaDB.
    """
    texte, nb_pages = extraire_texte(pdf_bytes)

    if not texte.strip():
        raise ValueError(f"Le PDF '{filename}' ne contient pas de texte extractible. "
                         "Vérifier qu'il ne se compose pas d'une image.")
 
    chunks = decouper_en_chunks(texte, source=filename)

    # Un PDF dont tout le texte tient sous le seuil de decouper_en_chunks ne
    # produit aucun chunk : sans ce garde-fou, l'import répondait « importé avec
    # succès — 0 chunks créés », un succès affiché pour un non-événement.
    if not chunks:
        raise ValueError(
            f"Le PDF '{filename}' contient trop peu de texte pour être indexé "
            "(quelques mots seulement). Il s'agit probablement de pages en image."
        )

    return {
        "chunks": chunks,
        "pages": nb_pages
    }