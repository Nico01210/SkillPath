from backend.config import settings
from backend.models.schemas import Erreur, CoursLie
from backend.services import rag_service
 
 
# ── MODE MOCK ─────────────────────────────────────────────────────────────────
# Passe à False quand tu as ta clé OpenAI dans le .env
MOCK_MODE = True
# ──────────────────────────────────────────────────────────────────────────────
 
 
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
    from openai import OpenAI
    import json
 
    client = OpenAI(api_key=settings.openai_api_key)
 
    # Contexte RAG — cours pertinents injectés dans le prompt
    contexte = rag_service.construire_contexte([
        "qualité du code", "bonnes pratiques", "clean code"
    ])
 
    prompt_systeme = """Tu es un coach de code pour étudiant en reconversion.
Analyse le code fourni et identifie les erreurs et mauvaises pratiques.
Réponds UNIQUEMENT en JSON valide, sans markdown, sans texte autour.
Format attendu :
[
  {
    "niveau": "critique" | "avertissement",
    "titre": "Titre court de l'erreur",
    "ligne": 42,
    "description": "Explication claire pour un étudiant débutant",
    "extrait": "bout de code fautif"
  }
]"""
 
    prompt_utilisateur = f"""Fichier : {filename}
 
{contexte}
 
Code à analyser :
{contenu}"""
 
    reponse = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": prompt_systeme},
            {"role": "user", "content": prompt_utilisateur}
        ],
        max_tokens=1000,
        temperature=0.2  # 0.2 = réponses cohérentes, peu créatives — bon pour l'analyse
    )
 
    texte = reponse.choices[0].message.content
    erreurs_brutes = json.loads(texte)
 
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