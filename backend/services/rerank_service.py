"""
Tri des extraits de cours candidats par le LLM.

Pourquoi cette étape existe : la recherche vectorielle mesure une proximité de
vocabulaire, pas une pertinence pédagogique. Mesuré sur les cours de test, le
meilleur score d'une erreur SANS cours correspondant dans l'index (injection SQL,
alors qu'aucun cours de sécurité n'est importé) atteignait 0,461, tandis qu'un
vrai match (`open()` sans `with` → cours sur les exceptions) plafonnait à 0,458.
Aucun seuil ne peut donc séparer les deux : « requête », « recherche »,
« malveillant » rapprochent mécaniquement l'injection SQL d'un cours REST.

D'où le schéma classique récupération large + tri : ChromaDB ramène beaucoup de
candidats avec un seuil bas, et un appel LLM tranche « cet extrait enseigne-t-il
la notion en jeu ? », avec « aucun » comme réponse légitime.
"""

from backend.config import settings
from openai import OpenAI, OpenAIError

import json
import logging


log = logging.getLogger(__name__)

# Nombre max d'extraits conservés par erreur — au-delà, le bloc « Cours à relire »
# devient une liste de liens que personne n'ouvre.
MAX_COURS_PAR_ERREUR = 3

# Longueur d'extrait envoyée au trieur. Un chunk fait ~180 mots ; 700 caractères
# suffisent à juger du sujet et bornent le coût de l'appel.
EXTRAIT_MAX_CHARS = 700

# Plafond du nombre d'extraits distincts soumis en un appel. La récupération est
# volontairement large (RECALL_N par erreur), donc un fichier à 6 erreurs peut
# produire beaucoup de candidats : ce plafond borne le coût. Au-delà, on écarte
# les moins bien classés — et on le journalise, pour qu'une coupe ne passe jamais
# pour une couverture complète.
MAX_EXTRAITS_ENVOYES = 60

SCHEMA_RATTACHEMENTS = {
    "name": "rattachements_cours",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "rattachements": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "erreur": {
                            "type": "integer",
                            "description": (
                                "Numéro de l'erreur tel qu'affiché dans le message, "
                                "en commençant à 1. Jamais 0."
                            ),
                        },
                        # Nommée AVANT d'examiner les extraits : sans cet ancrage,
                        # le modèle juge « est-ce du même domaine ? » et accepte un
                        # passage sur la sécurité des API pour une injection SQL.
                        # Avec, il compare deux notions nommées.
                        "notion_a_revoir": {
                            "type": "string",
                            "description": (
                                "La notion précise que l'étudiant doit revoir pour "
                                "corriger cette erreur, en quelques mots "
                                "(ex: « requêtes SQL paramétrées »)."
                            ),
                        },
                        "extraits": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    # Générée AVANT le numéro : le modèle doit
                                    # formuler ce que l'extrait enseigne avant de
                                    # s'engager, ce qui l'empêche de retenir un
                                    # extrait par simple proximité de vocabulaire.
                                    "notion_enseignee": {"type": "string"},
                                    "traite_la_notion": {"type": "boolean"},
                                    "numero": {"type": "integer"},
                                },
                                "required": [
                                    "notion_enseignee",
                                    "traite_la_notion",
                                    "numero",
                                ],
                                "additionalProperties": False,
                            },
                        },
                    },
                    "required": ["erreur", "notion_a_revoir", "extraits"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["rattachements"],
        "additionalProperties": False,
    },
}

PROMPT_SYSTEME = """Tu tries des extraits de cours pour un étudiant en programmation.

On te donne des erreurs détectées dans son code, et des extraits de ses cours
remontés par une recherche vectorielle. Cette recherche est bruitée : elle
rapproche des textes qui partagent du vocabulaire sans traiter le même sujet.

Procède erreur par erreur, en deux temps :

1. Nomme d'abord, dans notion_a_revoir, la notion précise que l'étudiant doit
   revoir pour corriger cette erreur — avant de regarder les extraits. Sois
   précis : « requêtes SQL paramétrées », pas « la sécurité » ; « gestionnaire de
   contexte with », pas « les fichiers ».
2. Puis, pour chaque extrait, mets traite_la_notion à true seulement si le
   passage traite de CETTE notion nommée. Si l'extrait parle d'autre chose, même
   du même domaine général, mets false — il sera écarté.

Il n'est PAS nécessaire que l'extrait décrive le cas exact de l'étudiant : un
chapitre sur les annotations de type répond à une erreur « pas de type hints »,
même s'il ne parle pas de sa classe à lui. C'est le sujet qui compte.

En revanche, ne suffisent PAS à retenir un extrait :
- partager du vocabulaire avec l'erreur (« requête », « liste », « erreur »,
  « malveillant », « sécurité ») sans traiter la notion
- traiter le même domaine général en passant à côté de la notion : un cours sur
  les API REST qui mentionne « Sécurité : rate limit, CORS » ne traite PAS des
  requêtes SQL paramétrées, donc il ne répond pas à une injection SQL
- énumérer des problèmes voisins sans aborder celui-ci : un tableau de code
  smells (God object, magic numbers) ne traite pas du partage d'état entre
  instances

Règles :
- Au maximum 3 extraits retenus par erreur, du plus utile au moins utile
- Une liste vide, ou une liste où tout est à false, est une réponse NORMALE et
  attendue : elle signifie que le cours correspondant n'a pas été importé. Un
  extrait hors sujet fait perdre à l'étudiant confiance dans tous les autres
  liens — mieux vaut ne rien proposer.
- Réponds une fois pour chaque erreur, et seulement pour les erreurs listées :
  le champ « erreur » reprend le numéro affiché (1, 2, 3…), jamais 0

Réponds au format défini par le schéma JSON fourni."""


def _bloc_erreurs(descriptions: list[str]) -> str:
    return "\n".join(
        f"Erreur {i + 1} : {d}" for i, d in enumerate(descriptions)
    )


def _bloc_extraits(textes: dict[int, dict]) -> str:
    lignes = []
    for num in sorted(textes):
        c = textes[num]
        texte = c["text"][:EXTRAIT_MAX_CHARS]
        lignes.append(f"Extrait {num} [{c['source']}] : {texte}")
    return "\n\n".join(lignes)


def filtrer(
    descriptions: list[str],
    candidats_par_erreur: list[list[dict]],
) -> list[list[dict]] | None:
    """
    Prend les candidats bruts de ChromaDB et retourne, pour chaque erreur, la
    sous-liste réellement pertinente (éventuellement vide).

    Retourne None si le tri n'a pas pu être effectué (pas de clé API, erreur
    réseau, réponse inexploitable) : l'appelant retombe alors sur un filtrage
    par seuil. Un tri indisponible ne doit jamais faire échouer un scan.
    """
    if not settings.openai_api_key:
        return None

    # Dédoublonne les candidats sur tout le fichier : le même chunk remonte
    # souvent sur plusieurs erreurs, l'envoyer une fois divise le coût.
    uniques: dict[str, dict] = {}
    for candidats in candidats_par_erreur:
        for c in candidats:
            cle = f"{c['source']}#{c['chunk_index']}"
            # Garde la meilleure occurrence : le score sert à trancher le plafond
            # ci-dessous, et un chunk peut scorer haut sur une erreur, bas sur une autre.
            if cle not in uniques or c["score"] > uniques[cle]["score"]:
                uniques[cle] = c

    if not uniques:
        return [[] for _ in descriptions]

    retenus_pour_envoi = sorted(uniques.items(), key=lambda kv: -kv[1]["score"])
    if len(retenus_pour_envoi) > MAX_EXTRAITS_ENVOYES:
        log.warning(
            "Tri des cours : %d candidats pour %d erreurs, plafonné à %d "
            "(les moins bien classés ne sont pas soumis)",
            len(retenus_pour_envoi), len(descriptions), MAX_EXTRAITS_ENVOYES,
        )
        retenus_pour_envoi = retenus_pour_envoi[:MAX_EXTRAITS_ENVOYES]

    numeros = {cle: i for i, (cle, _) in enumerate(retenus_pour_envoi, 1)}
    textes = {numeros[cle]: c for cle, c in retenus_pour_envoi}

    prompt = f"""{_bloc_erreurs(descriptions)}

--- Extraits de cours candidats ---

{_bloc_extraits(textes)}"""

    try:
        client = OpenAI(api_key=settings.openai_api_key)
        reponse = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": PROMPT_SYSTEME},
                {"role": "user", "content": prompt},
            ],
            max_tokens=800,
            temperature=0,  # tâche de tri : aucune créativité souhaitable
            response_format={"type": "json_schema", "json_schema": SCHEMA_RATTACHEMENTS},
        )
        if reponse.choices[0].finish_reason == "length":
            log.warning("Tri des cours tronqué — repli sur le filtrage par seuil")
            return None
        data = json.loads(reponse.choices[0].message.content)
    except (OpenAIError, json.JSONDecodeError, KeyError, IndexError) as exc:
        log.warning("Tri des cours indisponible (%s) — repli sur le seuil", exc)
        return None

    # Index des candidats de CHAQUE erreur, pour ne rattacher qu'un extrait
    # réellement proposé pour elle et garder son score exploitable.
    # Les candidats écartés par le plafond n'ont pas de numéro : on les omet
    # plutôt que de lever sur une clé absente.
    par_erreur = [
        {
            numeros[cle]: c
            for c in candidats
            if (cle := f"{c['source']}#{c['chunk_index']}") in numeros
        }
        for candidats in candidats_par_erreur
    ]

    rattachements = data.get("rattachements", [])

    # Le modèle numérote à partir de 1, comme le prompt le demande, mais émet
    # parfois un 0. Un 0 isolé est une entrée parasite qu'on écarte plus bas ;
    # un jeu complet numéroté 0..n-1 est un décalage global, qui rattacherait
    # SILENCIEUSEMENT chaque erreur aux cours de la précédente. On le détecte au
    # lieu de le subir.
    numerotes = [r.get("erreur") for r in rattachements]
    if numerotes and set(numerotes) == set(range(len(descriptions))):
        log.warning("Tri des cours : réponse indexée à 0, décalage corrigé")
        for r in rattachements:
            r["erreur"] = r.get("erreur", 0) + 1

    retenus: list[list[dict]] = [[] for _ in descriptions]
    for r in rattachements:
        i = r.get("erreur", 0) - 1
        if not 0 <= i < len(descriptions):
            log.warning("Tri : numéro d'erreur hors bornes (%s), ignoré", r.get("erreur"))
            continue
        # Le LLM ordonne du plus utile au moins utile ; on respecte son ordre.
        # On ne garde que ce qu'il a explicitement jugé sur le sujet : un extrait
        # listé mais marqué false est un rejet, pas un rattachement faible.
        garde = [
            par_erreur[i][x["numero"]]
            for x in r.get("extraits", [])
            if x.get("traite_la_notion") and x.get("numero") in par_erreur[i]
        ]
        retenus[i] = garde[:MAX_COURS_PAR_ERREUR]

    return retenus
