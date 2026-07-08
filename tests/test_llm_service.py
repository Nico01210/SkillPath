"""
Tests unitaires pour llm_service._parse_erreurs()
Aucune dépendance externe — pas d'appel OpenAI
"""
from backend.services.llm_service import _parse_erreurs


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


def test_parse_retourne_pas_une_liste():
    """Si GPT retourne un dict au lieu d'une liste → liste vide"""
    import json
    result = _parse_erreurs(json.dumps(ERREUR_VALIDE))
    assert result == []


def test_parse_chaine_vide():
    """Chaîne vide → liste vide sans crash"""
    result = _parse_erreurs("")
    assert result == []