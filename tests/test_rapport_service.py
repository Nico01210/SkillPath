"""
Tests unitaires pour rapport_service
Utilise unittest.mock pour isoler sqlite_service
"""
import json
import pytest
from unittest.mock import patch
from datetime import date


ANALYSE_MOCK = {
    "id": 1,
    "fichier": "main.py",
    "erreurs": [
        {
            "niveau": "critique",
            "titre": "Fonction trop longue",
            "fichier": "main.py",
            "ligne": 12,
            "description": "La fonction dépasse 20 lignes.",
            "extrait": "def process_data():\n    ...",
            "cours": []
        },
        {
            "niveau": "avertissement",
            "titre": "Variable non typée",
            "fichier": "main.py",
            "ligne": 5,
            "description": "Pas de type hint.",
            "extrait": "def calculate(data):",
            "cours": []
        }
    ],
    "created_at": "2026-07-08T10:00:00"
}


def test_rapport_du_jour_stats():
    """get_rapport_du_jour calcule bien critiques et avertissements"""
    with patch("backend.services.sqlite_service.get_analyses_par_date", return_value=[ANALYSE_MOCK]):
        from importlib import reload
        import backend.services.rapport_service as rs
        reload(rs)
        rapport = rs.get_rapport_du_jour()

    assert rapport.stats.critiques == 1
    assert rapport.stats.avertissements == 1
    assert rapport.stats.fichiers_analyses == 1


def test_rapport_du_jour_erreurs():
    """get_rapport_du_jour retourne bien toutes les erreurs"""
    with patch("backend.services.sqlite_service.get_analyses_par_date", return_value=[ANALYSE_MOCK]):
        from importlib import reload
        import backend.services.rapport_service as rs
        reload(rs)
        rapport = rs.get_rapport_du_jour()

    assert len(rapport.erreurs) == 2


def test_rapport_du_jour_vide():
    """Aucune analyse → stats à zéro"""
    with patch("backend.services.sqlite_service.get_analyses_par_date", return_value=[]):
        from importlib import reload
        import backend.services.rapport_service as rs
        reload(rs)
        rapport = rs.get_rapport_du_jour()

    assert rapport.stats.critiques == 0
    assert rapport.stats.avertissements == 0
    assert rapport.stats.fichiers_analyses == 0
    assert len(rapport.erreurs) == 0


def test_rapport_date_aujourdhui():
    """La date du rapport est bien aujourd'hui"""
    with patch("backend.services.sqlite_service.get_analyses_par_date", return_value=[]):
        from importlib import reload
        import backend.services.rapport_service as rs
        reload(rs)
        rapport = rs.get_rapport_du_jour()

    assert rapport.date == date.today()


def test_rapport_hier_stats():
    """get_rapport_hier calcule bien les stats d'hier"""
    with patch("backend.services.sqlite_service.get_analyses_par_date", return_value=[ANALYSE_MOCK]):
        from importlib import reload
        import backend.services.rapport_service as rs
        reload(rs)
        rapport = rs.get_rapport_hier()

    assert rapport.stats.critiques == 1
    assert rapport.stats.avertissements == 1


def test_rapport_hier_vide():
    """Aucune analyse hier → stats à zéro"""
    with patch("backend.services.sqlite_service.get_analyses_par_date", return_value=[]):
        from importlib import reload
        import backend.services.rapport_service as rs
        reload(rs)
        rapport = rs.get_rapport_hier()

    assert rapport.stats.critiques == 0
    assert len(rapport.erreurs) == 0


def test_generer_html_contient_date():
    """Le HTML exporté contient la date du rapport"""
    with patch("backend.services.sqlite_service.get_analyses_par_date", return_value=[]):
        from importlib import reload
        import backend.services.rapport_service as rs
        reload(rs)
        rapport = rs.get_rapport_du_jour()
        html = rs.generer_html(rapport)

    assert str(date.today()) in html


def test_generer_html_echappe_xss():
    """Les champs LLM sont bien échappés dans le HTML exporté"""
    analyse_xss = {
        **ANALYSE_MOCK,
        "erreurs": [{
            **ANALYSE_MOCK["erreurs"][0],
            "titre": "<script>alert('xss')</script>",
            "description": "<img src=x onerror=alert(1)>",
            "extrait": "<evil>",
        }]
    }
    with patch("backend.services.sqlite_service.get_analyses_par_date", return_value=[analyse_xss]):
        from importlib import reload
        import backend.services.rapport_service as rs
        reload(rs)
        rapport = rs.get_rapport_du_jour()
        html = rs.generer_html(rapport)

    assert "<script>" not in html
    assert "&lt;script&gt;" in html


# ── Déduplication des re-scans ────────────────────────
def _rapport_avec(analyses, resolutions=()):
    """Construit un rapport en isolant sqlite_service."""
    from importlib import reload
    import backend.services.rapport_service as rs
    with patch("backend.services.sqlite_service.get_analyses_par_date", return_value=analyses), \
         patch("backend.services.sqlite_service.get_resolutions", return_value=list(resolutions)), \
         patch("backend.services.sqlite_service.get_profil", return_value={"name": "Nico", "role": "Dev"}):
        reload(rs)
        rapport = rs.get_rapport_du_jour()
        return rapport, rs.generer_html(rapport)


def test_rapport_dedup_rescans_du_meme_fichier():
    """
    Scanner 3 fois le même fichier ne doit pas tripler les cartes ni les stats :
    la même erreur (fichier/ligne/niveau) partage une signature.
    """
    rapport, _ = _rapport_avec([ANALYSE_MOCK, ANALYSE_MOCK, ANALYSE_MOCK])

    assert len(rapport.erreurs) == 2          # et non 6
    assert rapport.stats.critiques == 1
    assert rapport.stats.avertissements == 1


def test_rapport_dedup_garde_le_titre_le_plus_recent():
    """Le titre affiché est celui de la détection la plus récente."""
    ancienne = {**ANALYSE_MOCK, "erreurs": [
        {**ANALYSE_MOCK["erreurs"][0], "titre": "Injection SQL potentielle"}
    ]}
    recente = {**ANALYSE_MOCK, "erreurs": [
        {**ANALYSE_MOCK["erreurs"][0], "titre": "Injection SQL possible"}
    ]}
    rapport, _ = _rapport_avec([ancienne, recente])

    assert len(rapport.erreurs) == 1
    assert rapport.erreurs[0].titre == "Injection SQL possible"


def test_rapport_compteur_coherent_avec_les_cartes():
    """
    Le total du compteur « X/Y résolues » doit égaler le nombre de cartes :
    c'est l'incohérence qui affichait 3 critiques, 3 cartes et « 1/2 résolues ».
    """
    sig = None
    rapport, _ = _rapport_avec([ANALYSE_MOCK])
    sig = rapport.erreurs[0].signature

    rapport, html = _rapport_avec([ANALYSE_MOCK, ANALYSE_MOCK], resolutions=[sig])
    total = rapport.stats.critiques + rapport.stats.avertissements

    assert total == len(rapport.erreurs) == 2
    assert "1/2 erreurs résolues" in html


def test_generer_html_marque_les_erreurs_resolues():
    """Une erreur résolue apparaît bien comme résolue dans l'export."""
    rapport, _ = _rapport_avec([ANALYSE_MOCK])
    sig = rapport.erreurs[0].signature

    _, html = _rapport_avec([ANALYSE_MOCK], resolutions=[sig])

    assert "✓ Résolu" in html