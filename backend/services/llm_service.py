from backend.config import settings
from backend.models.schemas import Erreur, CoursLie
from backend.services import rag_service, sqlite_service
from openai import OpenAI, RateLimitError, AuthenticationError, APIConnectionError

import logging
import json
import re


log = logging.getLogger(__name__)

MOCK_MODE = not bool(settings.openai_api_key)
log.warning("LLM — mode : %s", "MOCK" if MOCK_MODE else "OpenAI")

# Structured Outputs (response_format json_schema, strict) : l'API contraint la
# génération token par token pour garantir un JSON syntaxiquement valide ET
# conforme au schéma. Nécessaire car le modèle, livré à lui-même, casse parfois
# la syntaxe JSON (ex: guillemets non échappés quand la description cite du
# code contenant des guillemets, comme allow_origins=["*"]).
SCHEMA_ERREURS = {
    "name": "analyse_erreurs",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "erreurs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "niveau": {"type": "string", "enum": ["critique", "avertissement"]},
                        "titre": {"type": "string"},
                        "ligne": {"type": "integer"},
                        "description": {"type": "string"},
                        "extrait": {"type": "string"},
                    },
                    "required": ["niveau", "titre", "ligne", "description", "extrait"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["erreurs"],
        "additionalProperties": False,
    },
}

def _parse_erreurs(texte: str) -> list[dict]:
    texte = (texte or "").strip()
    # Retire les backticks ```json ... ``` si présents
    if texte.startswith("```"):
        texte = re.sub(r"^```(?:json)?\s*|\s*```$", "", texte, flags=re.MULTILINE).strip()
    try:
        data = json.loads(texte)
    except json.JSONDecodeError:
        log.warning("LLM non-JSON: %r", texte[:200])
        return []
    # Structured Outputs renvoie {"erreurs": [...]} ; on tolère aussi une liste
    # brute (mode dégradé sans json_schema).
    if isinstance(data, dict):
        data = data.get("erreurs")
    if not isinstance(data, list):
        return []
    # Valide que chaque erreur a les clés attendues
    champs = {"niveau", "titre", "ligne", "description", "extrait"}
    return [e for e in data if champs <= e.keys()]
 
def analyser_code(contenu: str, filename: str) -> list[Erreur]:
    """
    Envoie le code à OpenAI et retourne les erreurs détectées.
    En mode mock, retourne des erreurs fictives réalistes pour tester le pipeline.
    """
    if MOCK_MODE:
        return _mock_analyser(contenu, filename)
 
    return _openai_analyser(contenu, filename)
 
 
# ── MOCK ──────────────────────────────────────────────────────────────────────
 
def _mock_analyser(contenu: str, filename: str) -> list[Erreur]:
    """
    Simule une analyse OpenAI avec des erreurs fictives.
    Enrichit quand même via RAG pour tester le pipeline complet.
    """
    erreurs_brutes = [
                {
            "niveau": "critique",
            "titre": "Fonction trop longue",
            "ligne": 12,
            "description": "La fonction dépasse 20 lignes. Une fonction = une responsabilité.",
            "extrait": "def process_data():\n    # trop de logique ici..."
        },
        {
            "niveau": "avertissement",
            "titre": "Variable non typée",
            "ligne": 5,
            "description": "Pas de type hint sur les paramètres. Ajouter les annotations.",
            "extrait": "def calculate(data, threshold):\n    # manque : data: list, threshold: float"
        }
    ]
 
    return _enrichir_avec_rag(erreurs_brutes, filename)
 
 
# ── OPENAI (activé quand MOCK_MODE = False) ───────────────────────────────────
 
def _openai_analyser(contenu: str, filename: str) -> list[Erreur]:
    """
    Vrai appel OpenAI. Activé quand MOCK_MODE = False.
    """
 
    client = OpenAI(api_key=settings.openai_api_key)

    # Récupère les extraits de cours pertinents pour ANCRER l'analyse dans les
    # cours importés par l'étudiant (RAG). Vide si aucun cours n'est indexé.
    contexte_cours = rag_service.construire_contexte([contenu])

    prompt_systeme = """Tu es SkillPath, un coach de code bienveillant pour étudiant en reconversion professionnelle.

Ton rôle : analyser le code fourni et identifier les erreurs et mauvaises pratiques les plus importantes.

Règles strictes :
- Signale TOUTES les erreurs distinctes que tu trouves, jusqu'à 8. Ne t'arrête pas
  après une ou deux : un fichier soumis à l'analyse en contient couramment 5 ou 6,
  et en manquer donne à l'étudiant l'impression que son code est sain.
- Une erreur = une cause. Jamais deux entrées pour la même ligne ou le même
  problème sous deux angles : « fetch sans await » et « promesse non retournée »
  sur le même appel, c'est UNE erreur, pas deux.
- "critique" = bug potentiel, faille de sécurité, perte de données silencieuse,
  mutation d'état React, requête SQL non paramétrée. Un vrai bug reste critique
  même si le correctif est simple.
- "avertissement" = mauvaise pratique, lisibilité, maintenabilité
- La description doit expliquer POURQUOI c'est un problème ET comment le corriger, en termes simples
- L'extrait doit être le code fautif exact (pas le code corrigé)
- Adapte ton analyse au langage détecté (Python, Java, PHP, JS, JSX...)
- N'ignore que le cosmétique : nommage de variables simples, commentaires
  manquants, mise en forme.
- Deux exigences de justesse, plus importantes que le nombre de constats. Un
  étudiant en reconversion ne peut pas savoir qu'un constat est faux : il
  corrigera un non-problème ou retiendra une règle inexistante, et un seul
  constat visiblement erroné lui fait douter de tous les autres.
  1. Le problème doit être DÉMONTRABLE sur le code cité. Avant de retenir une
     erreur, vérifie qu'elle se produit vraiment ici. Exemple à ne pas commettre :
     annoncer qu'itérer sur le résultat de `fetchall()` échoue si la table est
     vide — parcourir une liste vide ne lève rien.
  2. Un avertissement doit reposer sur une règle OBJECTIVE, pas sur une
     préférence. « Ce nom serait plus clair », « une structure de données serait
     plus flexible », « ce serait mieux organisé » ne sont pas des erreurs : ne
     les signale pas.
  Dans le doute sur une faille de sécurité, un bug ou une ressource non libérée,
  signale. Dans le doute sur du confort ou du style, tais-toi.
- Les erreurs d'idiome comptent autant que les bugs, ne les saute pas :
  mutation d'un tableau pendant son itération, `forEach` + `push` au lieu de
  `map`/`reduce`, `sort()` qui mute la source, `await` dans une boucle au lieu de
  `Promise.all`, `fetch` sans vérifier `.ok`, exception trop générale, message
  d'erreur exposant les internes, valeur `None`/`undefined` non vérifiée,
  dépendance manquante dans `useEffect`, absence de cleanup, `key={index}`,
  état dérivé stocké au lieu d'être calculé, absence d'annotations de type,
  signature à plus de 4 paramètres.
- Priorise ce qui compte pour le métier visé par l'étudiant (indiqué en tête du
  message) et calibre ton vocabulaire sur son niveau

Réponds au format défini par le schéma JSON fourni."""

    # Le profil oriente l'analyse : les priorités d'un « développeur back-end »
    # ne sont pas celles d'un « intégrateur web ».
    profil = sqlite_service.get_profil()
    bloc_profil = f"Étudiant : {profil['name']} — métier visé : {profil['role']}\n"

    bloc_cours = f"{contexte_cours}\n\n" if contexte_cours else ""
    prompt_utilisateur = f"""{bloc_profil}Fichier : {filename}

{bloc_cours}Code à analyser :
{contenu}"""

    try:
        reponse = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": prompt_systeme},
                {"role": "user", "content": prompt_utilisateur}
            ],
            # 3000 et non 2000 : jusqu'à 8 erreurs décrites, un plafond trop bas
            # tronque le JSON et fait échouer le scan en 422 (voir finish_reason).
            max_tokens=3000,
            # 0 et non 0.2 : à 0.2, le même fichier donnait 5 erreurs à un scan et
            # 1 au suivant. L'analyse est une tâche d'extraction, la variabilité
            # n'y apporte rien et rend l'outil peu crédible pour l'étudiant.
            temperature=0,
            response_format={"type": "json_schema", "json_schema": SCHEMA_ERREURS}
        )
    except RateLimitError as exc:
        # 429 insufficient_quota : billing/quota OpenAI, pas un bug applicatif —
        # message explicite plutôt qu'une 500 « Erreur interne » trompeuse.
        raise ValueError(
            "Quota OpenAI dépassé. Vérifie ton plan et ta facturation sur "
            "platform.openai.com."
        ) from exc
    except AuthenticationError as exc:
        raise ValueError("Clé API OpenAI invalide ou manquante.") from exc
    except APIConnectionError as exc:
        raise ValueError("Impossible de joindre l'API OpenAI. Réessaie plus tard.") from exc

    choix = reponse.choices[0]
    # finish_reason == "length" → le JSON est coupé, donc inexploitable :
    # mieux vaut un message clair qu'une liste d'erreurs silencieusement tronquée.
    if choix.finish_reason == "length":
        raise ValueError(
            "L'analyse a été tronquée (fichier trop long). "
            "Découpe le fichier ou réessaie sur une partie plus courte."
        )

    erreurs_brutes = _parse_erreurs(choix.message.content)

    return _enrichir_avec_rag(erreurs_brutes, filename)
 
 
# ── COMMUN ────────────────────────────────────────────────────────────────────
 
def _enrichir_avec_rag(erreurs_brutes: list[dict], filename: str) -> list[Erreur]:
    """
    Prend les erreurs détectées (mock ou OpenAI) et ajoute les cours pertinents
    depuis ChromaDB via rag_service.
    """

    cours_par_erreur = rag_service.rattacher_cours(
        [e["description"] for e in erreurs_brutes]
    )

    erreurs = []
    for e, cours in zip(erreurs_brutes, cours_par_erreur):
        erreurs.append(Erreur(
            niveau=e["niveau"],
            titre=e["titre"],
            fichier=filename,
            ligne=e["ligne"],
            description=e["description"],
            extrait=e["extrait"],
            cours=cours
        ))
 
    return erreurs