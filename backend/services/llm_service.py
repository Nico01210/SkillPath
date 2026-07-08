from backend.config import settings
from backend.models.schemas import Erreur, CoursLie
from backend.services import rag_service
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
- Retourne entre 2 et 6 erreurs maximum — priorise les plus impactantes
- "critique" = bug potentiel, faille de sécurité, violation grave d'une convention
- "avertissement" = mauvaise pratique, lisibilité, maintenabilité
- La description doit expliquer POURQUOI c'est un problème ET comment le corriger, en termes simples
- L'extrait doit être le code fautif exact (pas le code corrigé)
- Adapte ton analyse au langage détecté (Python, Java, PHP, JS...)
- Ignore les erreurs triviales (nommage de variables simples, commentaires manquants)

Réponds au format défini par le schéma JSON fourni."""

    bloc_cours = f"{contexte_cours}\n\n" if contexte_cours else ""
    prompt_utilisateur = f"""Fichier : {filename}

{bloc_cours}Code à analyser :
{contenu}"""

    try:
        reponse = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": prompt_systeme},
                {"role": "user", "content": prompt_utilisateur}
            ],
            max_tokens=2000,
            temperature=0.2,  # 0.2 = réponses cohérentes, peu créatives — bon pour l'analyse
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
    erreurs = []
    for e in erreurs_brutes:
        cours = rag_service.trouver_cours_pertinents(e["description"])
 
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