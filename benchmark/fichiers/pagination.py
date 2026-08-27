"""
Calcul de pagination pour l'affichage de listes.

Toutes les fonctions de ce module sont pures : elles ne lisent ni ne
modifient aucun état global, et retournent systématiquement une nouvelle
valeur.
"""

from dataclasses import dataclass


TAILLE_PAGE_PAR_DEFAUT: int = 20
TAILLE_PAGE_MAX: int = 100

# Nombre de numéros de page affichés de part et d'autre de la page courante.
FENETRE_NAVIGATION: int = 2


@dataclass(frozen=True)
class Page:
    """Une page de résultats, immuable par construction."""

    numero: int
    taille: int
    total_elements: int

    @property
    def total_pages(self) -> int:
        """Nombre total de pages, au minimum une même sans résultat."""
        if self.total_elements == 0:
            return 1
        return -(-self.total_elements // self.taille)  # division entière par excès

    @property
    def decalage(self) -> int:
        """Index du premier élément de la page, pour un OFFSET SQL."""
        return (self.numero - 1) * self.taille

    @property
    def a_page_precedente(self) -> bool:
        return self.numero > 1

    @property
    def a_page_suivante(self) -> bool:
        return self.numero < self.total_pages


def borner_taille(taille: int) -> int:
    """
    Contraint une taille de page dans les limites acceptées.

    Args:
        taille: La taille demandée par l'appelant.

    Returns:
        Une taille comprise entre 1 et TAILLE_PAGE_MAX.
    """
    if taille < 1:
        return TAILLE_PAGE_PAR_DEFAUT
    return min(taille, TAILLE_PAGE_MAX)


def borner_numero(numero: int, total_pages: int) -> int:
    """
    Contraint un numéro de page dans les pages existantes.

    Args:
        numero: Le numéro demandé par l'appelant.
        total_pages: Le nombre de pages disponibles.

    Returns:
        Un numéro compris entre 1 et total_pages.
    """
    if numero < 1:
        return 1
    return min(numero, total_pages)


def construire_page(numero: int, taille: int, total_elements: int) -> Page:
    """
    Construit une page en corrigeant les valeurs hors limites.

    Args:
        numero: Le numéro de page demandé.
        taille: La taille de page demandée.
        total_elements: Le nombre total d'éléments à paginer.

    Returns:
        Une Page dont le numéro et la taille sont garantis valides.
    """
    taille_valide = borner_taille(taille)
    provisoire = Page(numero=1, taille=taille_valide, total_elements=total_elements)
    numero_valide = borner_numero(numero, provisoire.total_pages)

    return Page(
        numero=numero_valide,
        taille=taille_valide,
        total_elements=total_elements,
    )


def numeros_navigation(page: Page) -> list[int]:
    """
    Retourne les numéros de page à afficher dans la barre de navigation.

    La fenêtre est centrée sur la page courante, puis décalée si elle
    déborde d'un côté, afin de conserver une largeur constante.

    Args:
        page: La page courante.

    Returns:
        Les numéros à afficher, dans l'ordre croissant.
    """
    largeur = FENETRE_NAVIGATION * 2 + 1

    if page.total_pages <= largeur:
        return list(range(1, page.total_pages + 1))

    debut = page.numero - FENETRE_NAVIGATION
    if debut < 1:
        debut = 1
    elif debut + largeur - 1 > page.total_pages:
        debut = page.total_pages - largeur + 1

    return list(range(debut, debut + largeur))


def decouper(elements: list, page: Page) -> list:
    """
    Extrait les éléments correspondant à une page.

    Args:
        elements: La liste complète à paginer.
        page: La page à extraire.

    Returns:
        Une nouvelle liste contenant les éléments de la page. Une page
        au-delà des données produit une liste vide.
    """
    return elements[page.decalage : page.decalage + page.taille]


def resumer(page: Page) -> str:
    """
    Produit un résumé lisible de la position dans les résultats.

    Args:
        page: La page à résumer.

    Returns:
        Une phrase du type « 21 à 40 sur 137 résultats ».
    """
    if page.total_elements == 0:
        return "Aucun résultat"

    premier = page.decalage + 1
    dernier = min(page.decalage + page.taille, page.total_elements)
    return f"{premier} à {dernier} sur {page.total_elements} résultats"
