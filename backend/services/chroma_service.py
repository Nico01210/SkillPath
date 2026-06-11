import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions
from backend.config import settings


# Nom de la collection ChromaDB — comme une table en SQL
COLLECTION_NAME = "cours"


def get_client() -> chromadb.PersistentClient:
    return chromadb.PersistentClient(
        path=settings.chroma_db_path,
        settings=ChromaSettings(anonymized_telemetry=False),
    )
 
 
def get_collection():
    """
    Récupère (ou crée) la collection 'cours'.
    get_or_create_collection : si elle existe déjà, on la récupère — pas d'erreur.
 
    embedding_functions.DefaultEmbeddingFunction() utilise le modèle
    'all-MiniLM-L6-v2' en local — gratuit, pas d'appel API, ~80MB.
    C'est lui qui transforme le texte en vecteurs.
    """
    client = get_client()
    embedding_fn = embedding_functions.DefaultEmbeddingFunction()
 
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"}  # cosine = mesure de similarité sémantique
    )
 
 
def stocker_chunks(chunks: list[dict]) -> int:
    """
    Stocke une liste de chunks dans ChromaDB.
    Chaque chunk est automatiquement transformé en vecteur par l'embedding function.
 
    Retourne le nombre de chunks stockés.
    """
    collection = get_collection()
 
    # ChromaDB attend 3 listes parallèles :
    # - documents : les textes
    # - ids       : identifiants uniques (obligatoire)
    # - metadatas : infos supplémentaires (source, index...)
 
    documents = [c["text"] for c in chunks]
    ids = [f"{c['source']}__chunk_{c['chunk_index']}" for c in chunks]
    metadatas = [{"source": c["source"], "chunk_index": c["chunk_index"]} for c in chunks]
 
    # add() avec des ids existants lève une erreur — on utilise upsert()
    # upsert = insert si nouveau, update si existe déjà
    collection.upsert(
        documents=documents,
        ids=ids,
        metadatas=metadatas
    )
 
    return len(chunks)
 
 
def rechercher(query: str, n_resultats: int = 3) -> list[dict]:
    """
    Recherche sémantique : trouve les chunks les plus proches de la query.
    Utilisé par rag_service pour enrichir le prompt avec les cours pertinents.
 
    Exemple :
        query = "fonction qui fait trop de choses"
        → retourne les chunks sur le principe de responsabilité unique
    """
    collection = get_collection()
    n_resultats = min(n_resultats, collection.count())
    if n_resultats == 0:
        return []

    resultats = collection.query(
        query_texts=[query],
        n_results=n_resultats,
        include=["documents", "metadatas", "distances"]
    )
 
    # Reformate les résultats en liste de dicts lisibles
    chunks_trouves = []
    for i, doc in enumerate(resultats["documents"][0]):
        chunks_trouves.append({
            "text": doc,
            "source": resultats["metadatas"][0][i]["source"],
            "chunk_index": resultats["metadatas"][0][i]["chunk_index"],
            "score": round(1 - resultats["distances"][0][i], 3)
            # score = 1 - distance cosine → plus proche de 1 = plus pertinent
        })
 
    return chunks_trouves
 
 
def compter_chunks() -> int:
    """Utilitaire — retourne le nombre total de chunks stockés."""
    return get_collection().count()