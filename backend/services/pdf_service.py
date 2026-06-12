import fitz  # PyMuPDF — fitz est le nom du module interne
from pathlib import Path
 
 
# Taille d'un chunk en nombre de mots
# 500 mots ≈ 1 page de cours — assez de contexte pour le RAG
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50  # mots partagés entre deux chunks consécutifs
                    # évite de couper une explication en plein milieu
 
 
def extraire_texte(pdf_bytes: bytes) -> str:
    """
    Lit un PDF depuis ses bytes bruts et retourne tout le texte.
    On reçoit des bytes car le fichier vient d'un upload FastAPI.
    """
    # fitz.open avec stream= lit depuis la mémoire, pas depuis un fichier
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
 
    texte_complet = []
    for page in doc:
        texte_complet.append(page.get_text())
 
    doc.close()
    return "\n".join(texte_complet)
 
 
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
 
 
def traiter_pdf(pdf_bytes: bytes, filename: str) -> list[dict]:
    """
    Fonction principale appelée par import_router.
    Lit le PDF et retourne les chunks prêts pour ChromaDB.
    """
    texte = extraire_texte(pdf_bytes)
 
    if not texte.strip():
        raise ValueError(f"Le PDF '{filename}' ne contient pas de texte extractible. "
                         "Vérifier qu'il ne se compose pas d'une image.")
 
    chunks = decouper_en_chunks(texte, source=filename)
    return chunks