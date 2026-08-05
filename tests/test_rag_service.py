"""
Tests unitaires pour rag_service.titre_lisible()

Le titre est le seul texte visible sur les tags « Cours à relire » :
« Algorithmie.pdf — chunk 0 » n'apprend rien au lecteur.
"""
from backend.services.rag_service import titre_lisible, TITRE_APERCU_MAX


def test_titre_retire_extension_pdf():
    titre = titre_lisible("Algorithmie.pdf", 0, "Les types de variables en Java sont nombreux")
    assert titre.startswith("Algorithmie — ")
    assert ".pdf" not in titre


def test_titre_utilise_le_debut_du_contenu():
    titre = titre_lisible("Cours.pdf", 2, "Le principe de responsabilite unique")
    assert "Le principe de responsabilite unique" in titre


def test_titre_tronque_sur_une_frontiere_de_mot():
    texte = "Le principe de responsabilite unique impose qu une classe n ait qu une seule raison de changer"
    titre = titre_lisible("Cours.pdf", 0, texte)
    apercu = titre.split(" — ", 1)[1]
    assert apercu.endswith("…")
    assert len(apercu) <= TITRE_APERCU_MAX + 1
    # Pas de mot coupé en deux
    assert texte.startswith(apercu[:-1].rstrip())


def test_titre_aplatit_les_espaces():
    titre = titre_lisible("Cours.pdf", 0, "  plusieurs   espaces \n et sauts de ligne  ")
    assert "  " not in titre
    assert "\n" not in titre


def test_titre_repli_si_texte_vide():
    """Sans texte exploitable, on garde un repère de position lisible."""
    assert titre_lisible("Cours.pdf", 0, "") == "Cours — extrait 1"
    assert titre_lisible("Cours.pdf", 4, "  ") == "Cours — extrait 5"


def test_titre_repli_si_texte_trop_court():
    assert titre_lisible("Cours.pdf", 0, "abc") == "Cours — extrait 1"


def test_titre_source_sans_extension():
    assert titre_lisible("notes", 1, "") == "notes — extrait 2"
