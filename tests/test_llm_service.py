"""
Tests unitaires pour llm_service._parse_erreurs() et _openai_analyser()
"""
from unittest.mock import MagicMock, patch

from backend.services.llm_service import _parse_erreurs, _openai_analyser


ERREUR_VALIDE = {
    "niveau": "critique",
    "titre": "Fonction trop longue",
    "ligne": 12,
    "description": "La fonction dépasse 20 lignes.",
    "extrait": "def process_data():\n    ..."
}


def test_parse_json_valide():
    """JSON propre → retourne la liste correctement"""
    import json
    result = _parse_erreurs(json.dumps([ERREUR_VALIDE]))
    assert len(result) == 1
    assert result[0]["titre"] == "Fonction trop longue"
    assert result[0]["niveau"] == "critique"


def test_parse_avec_backticks_json():
    """GPT wrappe parfois dans ```json ... ``` — doit être stripped"""
    import json
    contenu = f"```json\n{json.dumps([ERREUR_VALIDE])}\n```"
    result = _parse_erreurs(contenu)
    assert len(result) == 1


def test_parse_avec_backticks_simples():
    """Variante avec ``` sans 'json'"""
    import json
    contenu = f"```\n{json.dumps([ERREUR_VALIDE])}\n```"
    result = _parse_erreurs(contenu)
    assert len(result) == 1


def test_parse_json_invalide():
    """JSON cassé → retourne liste vide sans crash"""
    result = _parse_erreurs("ceci n'est pas du JSON")
    assert result == []


def test_parse_liste_vide():
    """Liste vide valide → retourne liste vide"""
    result = _parse_erreurs("[]")
    assert result == []


def test_parse_champs_manquants():
    """Erreur sans tous les champs requis → filtrée"""
    import json
    incomplet = [{"niveau": "critique", "titre": "Test"}]  # manque ligne, description, extrait
    result = _parse_erreurs(json.dumps(incomplet))
    assert result == []


def test_parse_filtre_champs_invalides_et_garde_valides():
    """Mix valide + invalide → garde seulement le valide"""
    import json
    erreurs = [
        ERREUR_VALIDE,
        {"niveau": "critique", "titre": "Incomplet"}  # invalide
    ]
    result = _parse_erreurs(json.dumps(erreurs))
    assert len(result) == 1
    assert result[0]["titre"] == "Fonction trop longue"


def test_parse_enveloppe_structured_outputs():
    """Format Structured Outputs {"erreurs": [...]} → erreurs extraites"""
    import json
    result = _parse_erreurs(json.dumps({"erreurs": [ERREUR_VALIDE]}))
    assert len(result) == 1
    assert result[0]["titre"] == "Fonction trop longue"


def test_parse_retourne_pas_une_liste():
    """Si GPT retourne un dict sans clé "erreurs" → liste vide"""
    import json
    result = _parse_erreurs(json.dumps(ERREUR_VALIDE))
    assert result == []


def test_parse_chaine_vide():
    """Chaîne vide → liste vide sans crash"""
    result = _parse_erreurs("")
    assert result == []


def _reponse_openai(finish_reason: str, contenu: str = "[]"):
    choix = MagicMock(finish_reason=finish_reason)
    choix.message.content = contenu
    return MagicMock(choices=[choix])


@patch("backend.services.llm_service.sqlite_service")
@patch("backend.services.llm_service.rag_service")
@patch("backend.services.llm_service.OpenAI")
def test_openai_reessaie_apres_troncature(mock_openai_cls, mock_rag, mock_sqlite):
    """finish_reason == 'length' au 1er essai, correct au 2e → pas d'erreur, pas de 2e appel gaspillé"""
    mock_sqlite.get_profil.return_value = {"name": "Ada", "role": "backend"}
    mock_rag.construire_contexte.return_value = ""
    mock_rag.rattacher_cours.return_value = []

    client = MagicMock()
    client.chat.completions.create.side_effect = [
        _reponse_openai("length", ""),
        _reponse_openai("stop", "[]"),
    ]
    mock_openai_cls.return_value = client

    resultat = _openai_analyser("print('ok')", "exemple.py")

    assert resultat == []
    assert client.chat.completions.create.call_count == 2


@patch("backend.services.llm_service.sqlite_service")
@patch("backend.services.llm_service.rag_service")
@patch("backend.services.llm_service.OpenAI")
def test_openai_echoue_si_toujours_tronque(mock_openai_cls, mock_rag, mock_sqlite):
    """Deux troncatures de suite → message d'erreur explicite, pas de 3e tentative"""
    mock_sqlite.get_profil.return_value = {"name": "Ada", "role": "backend"}
    mock_rag.construire_contexte.return_value = ""

    client = MagicMock()
    client.chat.completions.create.side_effect = [
        _reponse_openai("length", ""),
        _reponse_openai("length", ""),
    ]
    mock_openai_cls.return_value = client

    try:
        _openai_analyser("print('ok')", "exemple.py")
        assert False, "devrait lever ValueError"
    except ValueError as exc:
        assert "tronqu" in str(exc)

    assert client.chat.completions.create.call_count == 2