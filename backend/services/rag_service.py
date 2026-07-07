from backend.models.schemas import CoursLie
from backend.services import chroma_service
RELEVANCE_THRESHOLD = 0.3
 
 
def trouver_cours_pertinents(description_erreur: str, n: int = 3) -> list[CoursLie]:
    """
    Prend la description d'une erreur détectée dans le code
    et retourne les chunks de cours les plus pertinents depuis ChromaDB.
 
    Exemple :
        description_erreur = "La fonction fait 87 lignes, trop de responsabilités"
        → retourne les chunks sur le principe de responsabilité unique (SRP)
          même si le mot "SRP" n'apparaît pas dans la description
    """
 
    # Vérifie qu'il y a des cours importés avant de chercher
    if chroma_service.compter_chunks() == 0:
        return []
 
    resultats = chroma_service.rechercher(description_erreur, n_resultats=n)
 
    cours = []
    for r in resultats:
        # Ne garde que les résultats suffisamment pertinents
        # score < RELEVANCE_THRESHOLD = trop éloigné sémantiquement, on l'ignore
        if r["score"] >= RELEVANCE_THRESHOLD:
            cours.append(CoursLie(
                titre=f"{r['source']} — chunk {r['chunk_index']}",
                chunk_id=chroma_service.chunk_id(r["source"], r["chunk_index"])
            ))
 
    return cours
 
 
def construire_contexte(descriptions_erreurs: list[str], n_par_query: int = 4) -> str:
    """
    Agrège les chunks pertinents pour toutes les erreurs d'un fichier
    en un bloc de texte injecté dans le prompt OpenAI.

    Retourne une chaîne formatée comme :
    --- Cours pertinents ---
    [Source: cours_python.pdf — chunk 2]
    "En Python, une fonction ne doit pas dépasser..."
    ...
    """
    if chroma_service.compter_chunks() == 0:
        return ""

    # Déduplique les chunks — une même règle peut matcher plusieurs erreurs
    chunks_vus = set()
    blocs = []

    for description in descriptions_erreurs:
        resultats = chroma_service.rechercher(description, n_resultats=n_par_query)
        for r in resultats:
            cid = chroma_service.chunk_id(r["source"], r["chunk_index"])
            if cid not in chunks_vus and r["score"] >= RELEVANCE_THRESHOLD:
                chunks_vus.add(cid)
                blocs.append(
                    f"[Source: {r['source']} — chunk {r['chunk_index']}]\n{r['text']}"
                )
 
    if not blocs:
        return ""
 
    return "--- Cours pertinents ---\n\n" + "\n\n".join(blocs)