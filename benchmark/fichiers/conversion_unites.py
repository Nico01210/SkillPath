"""
Conversion d'unités de mesure entre systèmes métrique et impérial.

Toutes les fonctions de ce module sont pures : elles ne lisent ni ne
modifient aucun état global, et retournent systématiquement une nouvelle
valeur. Elles sont donc sûres en contexte concurrent.
"""

from dataclasses import dataclass
from typing import Literal


# Facteurs de conversion vers l'unité de référence du système métrique.
# Longueur : le mètre. Masse : le kilogramme.
FACTEURS_LONGUEUR: dict[str, float] = {
    "mm": 0.001,
    "cm": 0.01,
    "m": 1.0,
    "km": 1000.0,
    "pouce": 0.0254,
    "pied": 0.3048,
    "mile": 1609.344,
}

FACTEURS_MASSE: dict[str, float] = {
    "mg": 0.000001,
    "g": 0.001,
    "kg": 1.0,
    "tonne": 1000.0,
    "once": 0.028349523125,
    "livre": 0.45359237,
}

# Nombre de décimales conservées par défaut à l'affichage.
PRECISION_PAR_DEFAUT: int = 4

TypeGrandeur = Literal["longueur", "masse"]


@dataclass(frozen=True)
class Mesure:
    """Une valeur associée à son unité, immuable par construction."""

    valeur: float
    unite: str

    def __str__(self) -> str:
        return f"{self.valeur} {self.unite}"


class UniteInconnueError(ValueError):
    """Levée lorsqu'une unité ne figure pas dans la table de conversion."""


def unites_disponibles(grandeur: TypeGrandeur) -> list[str]:
    """
    Retourne les unités reconnues pour une grandeur donnée.

    Args:
        grandeur: Le type de grandeur, longueur ou masse.

    Returns:
        Les noms d'unités, triés par ordre alphabétique.
    """
    table = FACTEURS_LONGUEUR if grandeur == "longueur" else FACTEURS_MASSE
    return sorted(table)


def _table_de(grandeur: TypeGrandeur) -> dict[str, float]:
    """Retourne la table de facteurs correspondant à une grandeur."""
    return FACTEURS_LONGUEUR if grandeur == "longueur" else FACTEURS_MASSE


def _facteur(unite: str, grandeur: TypeGrandeur) -> float:
    """
    Retourne le facteur de conversion d'une unité vers l'unité de référence.

    Args:
        unite: Le nom de l'unité recherchée.
        grandeur: Le type de grandeur concerné.

    Returns:
        Le facteur multiplicatif vers le mètre ou le kilogramme.

    Raises:
        UniteInconnueError: Si l'unité n'est pas reconnue.
    """
    table = _table_de(grandeur)
    normalisee = unite.strip().lower()

    if normalisee not in table:
        connues = ", ".join(sorted(table))
        raise UniteInconnueError(
            f"Unité '{unite}' inconnue pour une {grandeur}. Unités reconnues : {connues}"
        )

    return table[normalisee]


def convertir(
    valeur: float,
    depuis: str,
    vers: str,
    grandeur: TypeGrandeur = "longueur",
    precision: int = PRECISION_PAR_DEFAUT,
) -> float:
    """
    Convertit une valeur d'une unité vers une autre.

    La conversion passe par l'unité de référence du système métrique,
    ce qui évite de maintenir une table de tous les couples possibles.

    Args:
        valeur: La quantité à convertir.
        depuis: L'unité de départ.
        vers: L'unité d'arrivée.
        grandeur: Le type de grandeur, longueur ou masse.
        precision: Nombre de décimales du résultat.

    Returns:
        La valeur convertie, arrondie à la précision demandée.

    Raises:
        UniteInconnueError: Si l'une des deux unités n'est pas reconnue.
    """
    en_reference = valeur * _facteur(depuis, grandeur)
    resultat = en_reference / _facteur(vers, grandeur)
    return round(resultat, precision)


def convertir_mesure(
    mesure: Mesure,
    vers: str,
    grandeur: TypeGrandeur = "longueur",
    precision: int = PRECISION_PAR_DEFAUT,
) -> Mesure:
    """
    Convertit une mesure et retourne une nouvelle mesure.

    Args:
        mesure: La mesure d'origine, laissée intacte.
        vers: L'unité d'arrivée.
        grandeur: Le type de grandeur concerné.
        precision: Nombre de décimales du résultat.

    Returns:
        Une nouvelle Mesure exprimée dans l'unité demandée.
    """
    valeur = convertir(mesure.valeur, mesure.unite, vers, grandeur, precision)
    return Mesure(valeur=valeur, unite=vers)


def convertir_lot(
    mesures: list[Mesure],
    vers: str,
    grandeur: TypeGrandeur = "longueur",
    precision: int = PRECISION_PAR_DEFAUT,
) -> list[Mesure]:
    """
    Convertit une liste de mesures vers une unité commune.

    Chaque mesure est traitée indépendamment des autres : aucun état
    n'est partagé entre les conversions successives.

    Args:
        mesures: Les mesures à convertir.
        vers: L'unité d'arrivée commune.
        grandeur: Le type de grandeur concerné.
        precision: Nombre de décimales des résultats.

    Returns:
        Une nouvelle liste de mesures, dans le même ordre que l'entrée.
        Une liste vide en entrée produit une liste vide en sortie.
    """
    return [convertir_mesure(m, vers, grandeur, precision) for m in mesures]


def somme(
    mesures: list[Mesure],
    unite: str,
    grandeur: TypeGrandeur = "longueur",
    precision: int = PRECISION_PAR_DEFAUT,
) -> Mesure:
    """
    Additionne des mesures d'unités hétérogènes.

    Args:
        mesures: Les mesures à additionner.
        unite: L'unité dans laquelle exprimer le total.
        grandeur: Le type de grandeur concerné.
        precision: Nombre de décimales du total.

    Returns:
        Le total exprimé dans l'unité demandée. Une liste vide donne zéro.
    """
    total = sum(convertir(m.valeur, m.unite, unite, grandeur, precision) for m in mesures)
    return Mesure(valeur=round(total, precision), unite=unite)
