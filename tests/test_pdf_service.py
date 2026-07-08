"""
Tests unitaires pour pdf_service
Aucune dépendance externe — pas de vrai PDF nécessaire pour decouper_en_chunks
"""
from backend.services.pdf_service import decouper_en_chunks, CHUNK_SIZE, CHUNK_OVERLAP


def _generer_texte(nb_mots: int) -> str:
    """Génère un texte de nb_mots mots pour les tests."""
    return " ".join([f"mot{i}" for i in range(nb_mots)])


def test_chunk_texte_court():
    """Texte < CHUNK_SIZE → un seul chunk"""
    texte = _generer_texte(100)
    chunks = decouper_en_chunks(texte, "test.pdf")
    assert len(chunks) == 1


def test_chunk_texte_long():
    """Texte > CHUNK_SIZE → plusieurs chunks"""
    texte = _generer_texte(CHUNK_SIZE * 3)
    chunks = decouper_en_chunks(texte, "test.pdf")
    assert len(chunks) > 1


def test_chunk_structure():
    """Chaque chunk a les clés attendues"""
    texte = _generer_texte(100)
    chunks = decouper_en_chunks(texte, "test.pdf")
    for chunk in chunks:
        assert "text" in chunk
        assert "source" in chunk
        assert "chunk_index" in chunk


def test_chunk_source():
    """La source est bien propagée dans chaque chunk"""
    texte = _generer_texte(100)
    chunks = decouper_en_chunks(texte, "mon_cours.pdf")
    for chunk in chunks:
        assert chunk["source"] == "mon_cours.pdf"


def test_chunk_index_sequentiel():
    """Les chunk_index sont bien 0, 1, 2..."""
    texte = _generer_texte(CHUNK_SIZE * 3)
    chunks = decouper_en_chunks(texte, "test.pdf")
    for i, chunk in enumerate(chunks):
        assert chunk["chunk_index"] == i


def test_chunk_taille_minimum():
    """Les chunks de moins de 20 mots sont ignorés"""
    texte = _generer_texte(10)  # trop court
    chunks = decouper_en_chunks(texte, "test.pdf")
    assert chunks == []


def test_chunk_texte_vide():
    """Texte vide → aucun chunk"""
    chunks = decouper_en_chunks("", "test.pdf")
    assert chunks == []


def test_chunk_overlap():
    """Avec chevauchement, le nb de chunks est cohérent"""
    texte = _generer_texte(CHUNK_SIZE + CHUNK_OVERLAP + 50)
    chunks = decouper_en_chunks(texte, "test.pdf")
    # Doit produire au moins 2 chunks avec chevauchement
    assert len(chunks) >= 2


def test_chunk_contenu_non_vide():
    """Chaque chunk contient du texte"""
    texte = _generer_texte(200)
    chunks = decouper_en_chunks(texte, "test.pdf")
    for chunk in chunks:
        assert len(chunk["text"].strip()) > 0