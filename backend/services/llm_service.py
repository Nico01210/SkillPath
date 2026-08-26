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

    prompt_systeme = """Tu es SkillPath, un coach de code exigeant mais bienveillant pour étudiant en reconversion professionnelle.

Ta mission : identifier UNIQUEMENT les problèmes qu'un développeur senior
signalerait en code review et qui bloqueraient une merge request — pas des
erreurs à tout prix.

CRITÈRE DE SIGNALEMENT — pose-toi la question avant chaque erreur retenue :
« Est-ce que je bloquerais une merge request pour ça ? »
Si la réponse est non, ne la signale pas.

Si le code est propre, retourne une liste VIDE. C'est un résultat valide et
attendu — ne cherche pas une erreur à tout prix pour remplir la réponse.

À SIGNALER (jusqu'à 6, une entrée par cause distincte — jamais deux entrées
pour le même problème vu sous deux angles, ex. « fetch sans await » et
« promesse non retournée » sur le même appel, c'est UNE erreur) :
- Bug réel, comportement incorrect
- Faille de sécurité (injection SQL, requête non paramétrée, XSS, CORS
  permissif, secret en dur)
- Ressource non libérée, fuite mémoire, perte de données silencieuse
- Exception silencieuse qui masque une erreur, message d'erreur exposant les
  internes
- Mutation d'un état partagé, d'un paramètre, ou d'un état React
- Complexité algorithmique problématique (N+1, O(n²) évitable)
- Violation d'un idiome du langage : mutation d'un tableau pendant son
  itération, `forEach` + `push` au lieu de `map`/`reduce`, `sort()` qui mute la
  source, `await` dans une boucle au lieu de `Promise.all`, `fetch` sans
  vérifier `.ok`, dépendance manquante dans `useEffect`, absence de cleanup,
  `key={index}`, état dérivé stocké au lieu d'être calculé, signature à plus
  de 4 paramètres.
À NE JAMAIS SIGNALER :
- Préférences stylistiques, suggestions « on pourrait aussi », « il serait
  préférable de »
- Absence de gestion d'un cas qui ne peut pas se produire ici
- Documentation, docstring ou commentaire manquant, nommage de variable
  simple, mise en forme
- Micro-optimisation sans impact mesurable
- Syntaxe moderne correcte du langage (`str | None`, `list[str]`, `??`, `?.`...)
- Annotation de type absente en JavaScript non typé (le JSDoc suffit) — mais
  signale-la en Python ou TypeScript
- Code déjà correct que tu reformulerais simplement différemment

VÉRIFICATION OBLIGATOIRE avant de signaler : relis l'extrait exact que tu vas
citer. Si le reproche ne correspond pas à ce que fait réellement le code à cet
endroit, ne le signale pas. Exemple à ne pas commettre : annoncer qu'itérer
sur le résultat de `fetchall()` échoue si la table est vide — parcourir une
liste vide ne lève rien.

- "critique" = bug, faille de sécurité, perte de données silencieuse, mutation
  d'état React, requête SQL non paramétrée — même si le correctif est simple.
- "avertissement" = mauvaise pratique avérée, lisibilité, maintenabilité.
- La description doit expliquer POURQUOI c'est un problème ET comment le
  corriger, en termes simples.
- L'extrait doit être le code fautif exact (pas le code corrigé).
- Adapte ton analyse au langage détecté (Python, Java, PHP, JS, JSX...).
- Priorise ce qui compte pour le métier visé par l'étudiant (indiqué en tête
  du message) et calibre ton vocabulaire sur son niveau.

Réponds au format défini par le schéma JSON fourni."""

    # Le profil oriente l'analyse : les priorités d'un « développeur back-end »
    # ne sont pas celles d'un « intégrateur web ».
    profil = sqlite_service.get_profil()
    bloc_profil = f"Étudiant : {profil['name']} — métier visé : {profil['role']}\n"

    bloc_cours = f"{contexte_cours}\n\n" if contexte_cours else ""
    prompt_utilisateur = f"""{bloc_profil}Fichier : {filename}

{bloc_cours}Code à analyser :
{contenu}"""

    # Malgré temperature=0, la longueur de sortie de gpt-4o n'est pas
    # parfaitement stable d'un appel à l'autre (même fichier, même prompt) :
    # un second essai suffit en pratique à obtenir une réponse qui tient dans
    # max_tokens sans qu'un fichier réellement trop long ne s'en sorte pour
    # autant après 2 tentatives.
    NB_TENTATIVES_TRONQUE = 2

    for tentative in range(1, NB_TENTATIVES_TRONQUE + 1):
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
        if choix.finish_reason != "length":
            break
        log.warning(
            "LLM tronqué (tentative %d/%d) pour %s",
            tentative, NB_TENTATIVES_TRONQUE, filename,
        )
    else:
        # finish_reason == "length" → le JSON est coupé, donc inexploitable :
        # mieux vaut un message clair qu'une liste d'erreurs silencieusement tronquée.
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