"""
Service de validation et de normalisation d'adresses email.

Toutes les fonctions de ce module sont pures : elles ne lisent ni ne
modifient aucun état global, et retournent systématiquement une nouvelle
valeur. Elles sont donc sûres en contexte concurrent.
"""

import re
from dataclasses import dataclass


# Expression régulière conforme à la RFC 5322 (version simplifiée pragmatique)
MOTIF_EMAIL = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
)

# Domaines jetables les plus courants — liste volontairement restreinte,
# une V2 pourrait la charger depuis une source externe mise à jour.
DOMAINES_JETABLES: frozenset[str] = frozenset({
    "yopmail.com",
    "mailinator.com",
    "guerrillamail.com",
    "10minutemail.com",
})

LONGUEUR_MAX_EMAIL: int = 254  # limite imposée par la RFC 5321
LONGUEUR_MAX_PARTIE_LOCALE: int = 64

# Libellés de rejet — constantes fixes, sans donnée utilisateur ni détail interne.
RAISON_ADRESSE_VIDE: str = "Adresse vide"
RAISON_ARROBASE: str = "L'adresse doit contenir exactement un caractère arobase"
RAISON_TROP_LONGUE: str = "Adresse trop longue"
RAISON_PARTIE_LOCALE: str = "Partie locale trop longue"
RAISON_FORMAT_INVALIDE: str = "Format d'adresse invalide"
RAISON_DOMAINE_JETABLE: str = "Domaine jetable non autorisé"


@dataclass(frozen=True)
class ResultatValidation:
    """Résultat immuable d'une validation d'adresse email."""

    email: str
    est_valide: bool
    raison: str | None = None


def contient_une_seule_arobase(email: str) -> bool:
    """
    Indique si l'adresse contient exactement un caractère arobase.

    Args:
        email: L'adresse brute à examiner.

    Returns:
        True si l'adresse contient exactement une arobase.
    """
    return email.count("@") == 1


def normaliser(email: str) -> str:
    """
    Normalise une adresse email pour la comparaison et le stockage.

    La partie locale est conservée telle quelle car elle est sensible à la
    casse selon la RFC ; seul le domaine est mis en minuscules, conformément
    à l'usage.

    Cette fonction suppose que l'adresse contient exactement une arobase,
    ce que contient_une_seule_arobase() permet de vérifier au préalable.

    Args:
        email: L'adresse à normaliser, contenant une seule arobase.

    Returns:
        Une nouvelle chaîne normalisée, sans espaces superflus.
    """
    partie_locale, domaine = email.strip().split("@")
    return partie_locale + "@" + domaine.lower()


def extraire_partie_locale(email_normalise: str) -> str:
    """
    Retourne la partie locale d'une adresse normalisée.

    Args:
        email_normalise: Une adresse issue de normaliser().

    Returns:
        La portion située avant l'arobase.
    """
    return email_normalise.split("@")[0]


def extraire_domaine(email_normalise: str) -> str:
    """
    Retourne le domaine d'une adresse normalisée.

    Args:
        email_normalise: Une adresse issue de normaliser().

    Returns:
        La portion située après l'arobase, en minuscules.
    """
    return email_normalise.split("@")[1]


def est_jetable(email_normalise: str) -> bool:
    """
    Indique si l'adresse appartient à un service d'email jetable.

    Args:
        email_normalise: Une adresse issue de normaliser().

    Returns:
        True si le domaine figure dans la liste des domaines jetables.
    """
    return extraire_domaine(email_normalise) in DOMAINES_JETABLES


def determiner_raison_rejet(
    email_normalise: str, refuser_jetables: bool
) -> str | None:
    """
    Détermine la raison pour laquelle une adresse normalisée est rejetée.

    Args:
        email_normalise: Une adresse issue de normaliser().
        refuser_jetables: Si True, les domaines jetables sont rejetés.

    Returns:
        Le libellé de rejet correspondant, ou None si l'adresse est valide.
    """
    if len(email_normalise) > LONGUEUR_MAX_EMAIL:
        return RAISON_TROP_LONGUE

    if len(extraire_partie_locale(email_normalise)) > LONGUEUR_MAX_PARTIE_LOCALE:
        return RAISON_PARTIE_LOCALE

    if MOTIF_EMAIL.match(email_normalise) is None:
        return RAISON_FORMAT_INVALIDE

    if refuser_jetables and est_jetable(email_normalise):
        return RAISON_DOMAINE_JETABLE

    return None


def valider(email: str, refuser_jetables: bool = True) -> ResultatValidation:
    """
    Valide une adresse email et retourne un résultat détaillé.

    Args:
        email: L'adresse à valider.
        refuser_jetables: Si True, les domaines jetables sont rejetés.

    Returns:
        Un ResultatValidation immuable indiquant la validité et, en cas de
        rejet, un libellé de raison stable.
    """
    if not email.strip():
        return ResultatValidation(email, False, RAISON_ADRESSE_VIDE)

    if not contient_une_seule_arobase(email):
        return ResultatValidation(email, False, RAISON_ARROBASE)

    return _construire_resultat(normaliser(email), refuser_jetables)


def _construire_resultat(
    email_normalise: str, refuser_jetables: bool
) -> ResultatValidation:
    """
    Construit le résultat de validation d'une adresse déjà normalisée.

    Args:
        email_normalise: Une adresse issue de normaliser().
        refuser_jetables: Si True, les domaines jetables sont rejetés.

    Returns:
        Un ResultatValidation immuable.
    """
    raison = determiner_raison_rejet(email_normalise, refuser_jetables)
    return ResultatValidation(email_normalise, raison is None, raison)


def valider_lot(
    emails: list[str], refuser_jetables: bool = True
) -> list[ResultatValidation]:
    """
    Valide une liste d'adresses email.

    Chaque adresse est traitée indépendamment des autres : aucun état
    n'est partagé entre les validations successives.

    Args:
        emails: Les adresses à valider.
        refuser_jetables: Si True, les domaines jetables sont rejetés.

    Returns:
        Une nouvelle liste de résultats, dans le même ordre que les adresses
        fournies. Une liste vide en entrée produit une liste vide en sortie.
    """
    return [valider(email, refuser_jetables) for email in emails]


def extraire_emails_valides(
    resultats: list[ResultatValidation],
) -> list[str]:
    """
    Extrait les adresses des résultats marqués comme valides.

    Args:
        resultats: Les résultats issus de valider_lot().

    Returns:
        Une nouvelle liste contenant les adresses valides, doublons compris.
    """
    return [resultat.email for resultat in resultats if resultat.est_valide]


def dedupliquer_en_conservant_ordre(adresses: list[str]) -> list[str]:
    """
    Supprime les doublons en conservant l'ordre de première apparition.

    Un set seul ne convient pas ici car il ne garantit pas l'ordre.

    Args:
        adresses: Les adresses à dédupliquer.

    Returns:
        Une nouvelle liste sans doublon, dans l'ordre d'apparition d'origine.
    """
    uniques: list[str] = []
    deja_vues: set[str] = set()

    for adresse in adresses:
        if adresse not in deja_vues:
            deja_vues.add(adresse)
            uniques.append(adresse)

    return uniques


def filtrer_valides(emails: list[str]) -> list[str]:
    """
    Retourne les adresses valides, normalisées et dédupliquées.

    Args:
        emails: Les adresses à filtrer.

    Returns:
        Une nouvelle liste des adresses valides uniques, dans leur ordre
        de première apparition.
    """
    resultats = valider_lot(emails)
    valides = extraire_emails_valides(resultats)
    return dedupliquer_en_conservant_ordre(valides)
