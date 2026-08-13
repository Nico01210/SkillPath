import chromadb
import functools
import logging
import re
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions
from backend.config import settings


log = logging.getLogger(__name__)


def _embedding_fn():
    """
    Embeddings OpenAI si une clé est disponible, sinon repli sur le modèle local
    de Chroma (all-MiniLM-L6-v2) pour que le mode MOCK reste utilisable
    hors-ligne. Le local est nettement moins bon sur du français : c'est un
    filet de sécurité, pas la configuration cible.
    """
    if settings.openai_api_key:
        return embedding_functions.OpenAIEmbeddingFunction(
            api_key=settings.openai_api_key,
            model_name=settings.embedding_model,
        )

    log.warning(
        "Embeddings — pas de clé OpenAI : repli sur le modèle local "
        "(qualité dégradée sur les cours en français)."
    )
    return embedding_functions.DefaultEmbeddingFunction()


def _collection_name() -> str:
    """
    Nom de la collection ChromaDB — comme une table en SQL.

    Le nom porte le modèle d'embedding parce que deux modèles ne produisent ni
    la même dimension de vecteur ni le même espace sémantique : mélanger leurs
    vecteurs dans une collection donne, au mieux, une erreur de dimension et,
    au pire, des recherches silencieusement absurdes. Changer de modèle ouvre
    donc une collection vide — l'app affiche « 0 cours indexé » et un
    /import/reimporter-tout reconstruit l'index proprement.
    """
    if not settings.openai_api_key:
        return "cours__local_minilm"
    # Les noms de collection Chroma n'acceptent que [a-zA-Z0-9._-]
    slug = re.sub(r"[^a-zA-Z0-9._-]", "_", settings.embedding_model)
    return f"cours__{slug}"


def chunk_id(source: str, index: int) -> str:
    return f"{source}__chunk_{index}"

@functools.lru_cache(maxsize=1)
def get_collection():
    client = chromadb.PersistentClient(
        path=settings.chroma_db_path,
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    return client.get_or_create_collection(
        name=_collection_name(),
        embedding_function=_embedding_fn(),
        metadata={"hnsw:space": "cosine"}
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
    ids = [chunk_id(c["source"], c["chunk_index"]) for c in chunks]
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


def get_chunk(chunk_id: str) -> dict | None:
    """
    Récupère un chunk par son identifiant (celui produit par chunk_id()).
    Retourne None si l'id n'existe pas (cours supprimé de l'index, par ex.).
    Utilisé pour afficher l'extrait de cours quand on clique sur un tag.
    """
    res = get_collection().get(ids=[chunk_id], include=["documents", "metadatas"])
    if not res["ids"]:
        return None
    return {
        "chunk_id": chunk_id,
        "text": res["documents"][0],
        "source": res["metadatas"][0]["source"],
        "chunk_index": res["metadatas"][0]["chunk_index"],
    }


def supprimer_chunks(source: str) -> None:
    """Supprime tous les chunks associés à un fichier source donné."""
    get_collection().delete(where={"source": source})