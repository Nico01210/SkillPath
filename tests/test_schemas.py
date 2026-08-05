"""
Tests unitaires pour la signature d'erreur.

La signature est ce qui permet de retrouver une erreur d'un scan à l'autre :
c'est elle qui porte l'état « résolu » et le suivi de progression.
"""
from backend.models.schemas import Erreur, Profil, signature_erreur


def make_erreur(**overrides) -> Erreur:
    champs = {
        "niveau": "critique",
        "titre": "Injection SQL potentielle",
        "fichier": "app.py",
        "ligne": 12,
        "description": "Requête construite par concaténation.",
        "extrait": 'q = "SELECT * FROM users WHERE id = " + id',
        "cours": [],
    }
    return Erreur(**{**champs, **overrides})


def test_signature_stable_malgre_reformulation_du_titre():
    """
    Le titre est du texte libre généré par le LLM et varie d'un scan à l'autre.
    La signature ne doit pas bouger, sinon l'état « résolu » est perdu à chaque
    re-scan et la progression hebdomadaire ne s'accumule jamais.
    """
    a = make_erreur(titre="Injection SQL potentielle")
    b = make_erreur(titre="Injection SQL possible")

    assert a.signature == b.signature


def test_signature_stable_malgre_description_et_extrait():
    """Description et extrait varient aussi d'un scan à l'autre."""
    a = make_erreur(description="Concaténation dangereuse", extrait="q = ...")
    b = make_erreur(description="Requête non paramétrée", extrait="query = ...")

    assert a.signature == b.signature


def test_signature_distingue_les_lignes():
    assert make_erreur(ligne=12).signature != make_erreur(ligne=40).signature


def test_signature_distingue_les_fichiers():
    assert make_erreur(fichier="a.py").signature != make_erreur(fichier="b.py").signature


def test_signature_distingue_les_niveaux():
    """Deux problèmes de gravité différente sur la même ligne restent distincts."""
    critique = make_erreur(niveau="critique")
    avertissement = make_erreur(niveau="avertissement")

    assert critique.signature != avertissement.signature


def test_signature_erreur_coherente_avec_le_modele():
    """
    stats_service recalcule la signature depuis les dicts JSON stockés (les
    analyses enregistrées avant le changement de formule portent une signature
    obsolète). Les deux chemins doivent donner le même résultat.
    """
    e = make_erreur()
    assert e.signature == signature_erreur(e.fichier, e.ligne, e.niveau)


def test_signature_longueur_fixe():
    assert len(make_erreur().signature) == 16


# ── Profil ────────────────────────────────────────────
def test_initials_deux_mots():
    assert Profil(name="Nicolas P.", role="Dev").initials == "NP"


def test_initials_un_seul_mot():
    assert Profil(name="Nicolas", role="Dev").initials == "N"


def test_initials_nom_vide():
    assert Profil(name="", role="Dev").initials == "?"
