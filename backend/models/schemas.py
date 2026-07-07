import hashlib
from pydantic import BaseModel, computed_field
from datetime import date
from typing import Literal


# ─── IMPORT ───────────────────────────────────────────────
# Le frontend envoie un PDF, FastAPI répond avec ça :

class ImportResponse(BaseModel):
    filename: str       # nom du fichier importé
    chunks: int         # nombre de morceaux créés (ex: 12)
    message: str        # confirmation lisible
    pages: int


# ─── SCAN ─────────────────────────────────────────────────
# Une erreur détectée dans le code

class CoursLie(BaseModel):
    titre: str          # ex: "Chapitre 3 — Fonctions et SRP"
    chunk_id: str       # identifiant du morceau dans ChromaDB

class Erreur(BaseModel):
    niveau: Literal["critique", "avertissement"]
    titre: str          # ex: "Fonction trop longue"
    fichier: str        # ex: "main.py"
    ligne: int          # numéro de ligne
    description: str    # explication de l'erreur
    extrait: str        # bout de code fautif
    cours: list[CoursLie]  # cours à relire (vient du RAG)

    @computed_field
    @property
    def signature(self) -> str:
        """
        Identifiant stable d'une erreur, basé sur son contenu (fichier + titre +
        ligne). Permet de mémoriser qu'une erreur est « résolue » indépendamment
        de l'analyse dont elle provient : la même erreur re-détectée plus tard
        garde la même signature.
        """
        cle = f"{self.fichier}|{self.titre}|{self.ligne}"
        return hashlib.sha1(cle.encode("utf-8")).hexdigest()[:16]

# Ce que retourne POST /scan
class ScanResponse(BaseModel):
    fichier: str
    erreurs: list[Erreur]
    message: str        # ex: "3 erreurs détectées"


# ─── PROFIL ───────────────────────────────────────────────
# Entité unique (mono-utilisateur, pas de table users ni d'auth)

class Profil(BaseModel):
    name: str
    role: str

    @computed_field
    @property
    def initials(self) -> str:
        """Initiales depuis le nom, ex: 'Nicolas P.' -> 'NP'."""
        mots = [m for m in self.name.replace(".", "").split() if m]
        return "".join(m[0] for m in mots[:2]).upper() or "?"


# ─── RAPPORT ──────────────────────────────────────────────
# Agrégation de toutes les analyses de la journée

class StatsRapport(BaseModel):
    critiques: int
    avertissements: int
    fichiers_analyses: int
    cours_a_relire: int

# Ce que retourne GET /rapport
class RapportResponse(BaseModel):
    date: date
    stats: StatsRapport
    erreurs: list[Erreur]   # toutes les erreurs du jour


# ─── STATS DASHBOARD ──────────────────────────────────────
# Progression hebdomadaire et mensuelle
 
class PointCourbe(BaseModel):
    date: str               # ex: "2026-06-09"
    total_erreurs: int
    critiques: int
    avertissements: int
 
class ErreurRecurrente(BaseModel):
    titre: str              # nombre de fois détectée sur la période
    occurrences: int
    niveau: Literal["critique", "avertissement"]
 
class CoursFrequent(BaseModel):
    titre: str              # nombre de fois recommandé
    recommandations: int
 
# Ce que retourne GET /stats/dashboard
class StatsResponse(BaseModel):
    periode: str            # "semaine" ou "mois"
    date_debut: str
    date_fin: str
    total_fichiers: int
    total_erreurs: int
    courbe: list[PointCourbe]
    erreurs_recurrentes: list[ErreurRecurrente]
    cours_frequents: list[CoursFrequent]