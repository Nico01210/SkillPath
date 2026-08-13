from backend.models.schemas import CoursLie
from backend.services import chroma_service, rerank_service

# Le rattachement d'une erreur à ses cours se fait en deux temps :
# récupération large ici, puis tri par le LLM dans rerank_service.
#
# La similarité vectorielle seule ne suffit pas, et ce n'est pas une question de
# réglage : mesuré sur les cours de test, une erreur SANS cours correspondant
# dans l'index scorait 0,461 quand un vrai match plafonnait à 0,458. Un seuil
# unique garde donc forcément du bruit ou jette de vrais résultats. Le seuil
# n'est plus le juge : il ne sert qu'à borner le nombre de candidats envoyés au
# tri.
# Fenêtre large à dessein. Mesuré sur une erreur « pas de type hints » : le chunk
# qui s'intitule « Absence de type hints (Python) » sortait au rang 16 (0,437),
# derrière un passage sur le God Object (0,517). Le classement vectoriel n'est pas
# fiable au point de faire confiance à son top 8 ; c'est le tri qui décide, donc
# on lui soumet largement.
RECALL_N = 20

# Plancher de récupération — délibérément bas. Mieux vaut soumettre un candidat
# de trop au trieur, qui sait dire non, que de l'écarter ici sans recours.
RECALL_THRESHOLD = 0.32

# Seuil utilisé UNIQUEMENT quand le tri LLM est indisponible (mode MOCK, panne
# réseau). Filet de sécurité dégradé : il laisse passer des rattachements faux,
# c'est le compromis assumé pour qu'un scan aboutisse toujours.
FALLBACK_THRESHOLD = 0.42

# Longueur max de l'aperçu de contenu affiché dans un titre de cours
TITRE_APERCU_MAX = 42


def titre_lisible(source: str, chunk_index: int, texte: str = "") -> str:
    """
    Construit un libellé lisible pour un extrait de cours.

    « Algorithmie.pdf — chunk 0 » ne dit rien à la lecture : c'est pourtant le
    texte affiché sur les tags « Cours à relire ». On lui préfère le nom du
    cours suivi des premiers mots de l'extrait, ce qui donne
    « Algorithmie — Les types de variables en Java… ».

    Le chunking aplatit les retours à la ligne du PDF (`texte.split()`), donc il
    n'y a pas de « première ligne » à isoler : on prend un aperçu tronqué sur
    une frontière de mot. Sans texte exploitable, on retombe sur « extrait N ».
    """
    nom = source[:-4] if source.lower().endswith(".pdf") else source
    apercu = " ".join((texte or "").split())

    if len(apercu) < 12:
        return f"{nom} — extrait {chunk_index + 1}"

    if len(apercu) > TITRE_APERCU_MAX:
        coupe = apercu[:TITRE_APERCU_MAX].rsplit(" ", 1)[0]
        apercu = f"{coupe or apercu[:TITRE_APERCU_MAX]}…"

    return f"{nom} — {apercu}"



def _en_cours_lie(r: dict) -> CoursLie:
    return CoursLie(
        titre=titre_lisible(r["source"], r["chunk_index"], r["text"]),
        chunk_id=chroma_service.chunk_id(r["source"], r["chunk_index"]),
    )


def rattacher_cours(descriptions_erreurs: list[str]) -> list[list[CoursLie]]:
    """
    Rattache chaque erreur d'un fichier aux extraits de cours à relire.

    Retourne une liste parallèle à `descriptions_erreurs` : un élément par
    erreur, éventuellement vide (affiché « Aucun cours lié »).

    Exemple :
        "La fonction fait 87 lignes, trop de responsabilités"
        → les extraits sur la responsabilité unique (SRP), même si « SRP »
          n'apparaît pas dans la description

    Le tri se fait en un seul appel LLM pour tout le fichier : les mêmes chunks
    remontent sur plusieurs erreurs, les mutualiser divise le coût.
    """
    if chroma_service.compter_chunks() == 0 or not descriptions_erreurs:
        return [[] for _ in descriptions_erreurs]

    # 1. Récupération large — on préfère un candidat de trop au tri qu'un vrai
    #    résultat écarté ici sans recours.
    candidats = [
        [
            r for r in chroma_service.rechercher(d, n_resultats=RECALL_N)
            if r["score"] >= RECALL_THRESHOLD
        ]
        for d in descriptions_erreurs
    ]

    # 2. Tri par le LLM — le seul étage capable de répondre « aucun ».
    retenus = rerank_service.filtrer(descriptions_erreurs, candidats)

    # 3. Repli si le tri est indisponible : filtrage par seuil, dégradé mais
    #    jamais bloquant.
    if retenus is None:
        retenus = [
            [r for r in cands if r["score"] >= FALLBACK_THRESHOLD][
                : rerank_service.MAX_COURS_PAR_ERREUR
            ]
            for cands in candidats
        ]

    return [[_en_cours_lie(r) for r in cands] for cands in retenus]
 
 
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
            # Seuil de récupération, pas de pertinence : ce contexte sert à
            # ancrer le vocabulaire du prompt d'analyse, pas à être affiché à
            # l'étudiant. Un extrait approximatif y est sans conséquence.
            if cid not in chunks_vus and r["score"] >= RECALL_THRESHOLD:
                chunks_vus.add(cid)
                blocs.append(
                    f"[Source: {r['source']} — chunk {r['chunk_index']}]\n{r['text']}"
                )
 
    if not blocs:
        return ""
 
    return "--- Cours pertinents ---\n\n" + "\n\n".join(blocs)