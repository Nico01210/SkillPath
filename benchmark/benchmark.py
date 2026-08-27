#!/usr/bin/env python3
"""
SkillPath — banc d'essai de la qualité d'analyse.

Envoie un corpus de fichiers de référence à l'API SkillPath et compare
les erreurs détectées à celles attendues. Produit deux mesures :

  RAPPEL         — part des erreurs attendues effectivement détectées
  FAUX POSITIFS  — erreurs remontées sur les fichiers volontairement propres

Une erreur trouvée en plus du corpus sur un fichier bugué n'est pas comptée
comme un faux positif : elle peut être légitime, simplement non anticipée.
Seuls les fichiers propres permettent de trancher sans ambiguïté.

Cet outil est volontairement isolé de l'application : il ne l'appelle
que par HTTP, comme n'importe quel client externe. Le supprimer n'a
aucun effet sur SkillPath.

Usage :
    python benchmark.py
    python benchmark.py --url http://localhost:8000
    python benchmark.py --fichier gestion_stock.py   # un seul fichier
    python benchmark.py --json resultats.json        # export machine
"""

import argparse
import json
import sys
import unicodedata
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path


RACINE = Path(__file__).resolve().parent
DOSSIER_FICHIERS = RACINE / "fichiers"
ATTENDUS = RACINE / "attendus.yml"

URL_DEFAUT = "http://localhost:8000"
TIMEOUT = 120  # l'analyse passe par un LLM : prévoir large

# Seuils au-delà desquels on considère la configuration acceptable.
SEUIL_RAPPEL = 0.80
MAX_FAUX_POSITIFS = 0

ROUGE, ORANGE, VERT, GRIS, GRAS, RESET = (
    "\033[31m", "\033[33m", "\033[32m", "\033[90m", "\033[1m", "\033[0m"
)


# ── Modèle de données ─────────────────────────────────────────

@dataclass
class Attendu:
    """Une erreur que l'analyse doit trouver dans un fichier."""
    libelle: str
    mots_cles: list[str]


@dataclass
class Resultat:
    """Résultat de l'analyse d'un fichier du corpus."""
    nom: str
    trouves: list[str] = field(default_factory=list)
    manquants: list[str] = field(default_factory=list)
    faux_positifs: int = 0
    hors_corpus: int = 0
    total_detecte: int = 0
    erreur: str | None = None

    @property
    def est_propre(self) -> bool:
        """Un fichier propre est un fichier sans erreur attendue."""
        return not self.trouves and not self.manquants

    @property
    def nb_attendus(self) -> int:
        return len(self.trouves) + len(self.manquants)


# ── Chargement de la configuration ────────────────────────────

def normaliser(texte: str) -> str:
    """
    Met un texte sous forme comparable : minuscules, sans accents.

    Le modèle écrit indifféremment « détectée » ou « detectee »,
    « Injection SQL » ou « injection sql ».
    """
    sans_accents = unicodedata.normalize("NFD", texte)
    sans_accents = "".join(c for c in sans_accents if unicodedata.category(c) != "Mn")
    return sans_accents.lower()


def charger_attendus(chemin: Path) -> list[dict]:
    """
    Lit attendus.yml.

    PyYAML n'est pas requis : le format est plat et connu, un parseur
    minimal évite d'imposer une dépendance pour lancer le banc d'essai.
    """
    try:
        import yaml
        with chemin.open(encoding="utf-8") as f:
            return yaml.safe_load(f)["fichiers"]
    except ImportError:
        pass

    fichiers: list[dict] = []
    courant: dict | None = None
    attendu_courant: dict | None = None

    for ligne_brute in chemin.read_text(encoding="utf-8").splitlines():
        ligne = ligne_brute.split("#")[0].rstrip()
        if not ligne.strip():
            continue

        indent = len(ligne) - len(ligne.lstrip())
        contenu = ligne.strip()

        # Nouveau fichier du corpus
        if indent == 2 and contenu.startswith("- nom:"):
            if courant:
                fichiers.append(courant)
            courant = {"nom": contenu.split(":", 1)[1].strip(), "attendus": []}
            attendu_courant = None
            continue

        if courant is None:
            continue

        if contenu.startswith("description:"):
            courant["description"] = contenu.split(":", 1)[1].strip()
            continue

        if contenu.startswith("attendus:"):
            reste = contenu.split(":", 1)[1].strip()
            if reste == "[]":
                courant["attendus"] = []
            continue

        # Nouvelle erreur attendue
        if contenu.startswith("- libelle:"):
            attendu_courant = {"libelle": contenu.split(":", 1)[1].strip(), "mots_cles": []}
            courant["attendus"].append(attendu_courant)
            continue

        if contenu.startswith("mots_cles:") and attendu_courant is not None:
            brut = contenu.split(":", 1)[1].strip().strip("[]")
            attendu_courant["mots_cles"] = [m.strip() for m in brut.split(",") if m.strip()]

    if courant:
        fichiers.append(courant)
    return fichiers


# ── Appel à l'API ─────────────────────────────────────────────

def scanner(url: str, chemin: Path) -> list[dict]:
    """
    Envoie un fichier à POST /scan et retourne les erreurs détectées.

    Raises:
        RuntimeError: Si l'API est injoignable ou répond en erreur.
    """
    frontiere = "----SkillPathBench"
    entete = (
        f"--{frontiere}\r\n"
        f'Content-Disposition: form-data; name="fichier"; filename="{chemin.name}"\r\n'
        f"Content-Type: text/plain\r\n\r\n"
    )
    corps = b"".join([
        entete.encode(),
        chemin.read_bytes(),
        f"\r\n--{frontiere}--\r\n".encode(),
    ])

    requete = urllib.request.Request(
        url.rstrip("/") + "/scan/",
        data=corps,
        headers={"Content-Type": f"multipart/form-data; boundary={frontiere}"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(requete, timeout=TIMEOUT) as reponse:
            return json.loads(reponse.read()).get("erreurs", [])
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"API injoignable sur {url}") from exc


# ── Comparaison ───────────────────────────────────────────────

def erreur_correspond(erreur: dict, mots_cles: list[str]) -> bool:
    """
    Indique si une erreur détectée correspond à un attendu.

    On cherche dans le titre et la description réunis : le modèle place
    l'information tantôt dans l'un, tantôt dans l'autre. Tous les mots-clés
    doivent être présents.
    """
    texte = normaliser(f"{erreur.get('titre', '')} {erreur.get('description', '')}")
    return all(normaliser(mot) in texte for mot in mots_cles)


def evaluer(nom: str, attendus: list[Attendu], detectees: list[dict]) -> Resultat:
    """
    Compare les erreurs détectées aux erreurs attendues pour un fichier.

    Chaque erreur détectée ne peut satisfaire qu'un seul attendu, pour
    éviter qu'une erreur générique ne valide plusieurs lignes du corpus.
    """
    resultat = Resultat(nom=nom, total_detecte=len(detectees))
    deja_utilisees: set[int] = set()

    for attendu in attendus:
        correspondance = next(
            (
                i for i, err in enumerate(detectees)
                if i not in deja_utilisees and erreur_correspond(err, attendu.mots_cles)
            ),
            None,
        )
        if correspondance is None:
            resultat.manquants.append(attendu.libelle)
        else:
            deja_utilisees.add(correspondance)
            resultat.trouves.append(attendu.libelle)

    if attendus:
        # Erreurs légitimes non anticipées : signalées, jamais pénalisées.
        resultat.hors_corpus = len(detectees) - len(deja_utilisees)
    else:
        # Sur un fichier propre, seule une erreur critique est un faux positif :
        # un avertissement reste informatif, il ne fait pas échouer le banc d'essai.
        resultat.faux_positifs = sum(1 for e in detectees if e.get("niveau") == "critique")

    return resultat


# ── Affichage ─────────────────────────────────────────────────

def afficher_resultat(r: Resultat) -> None:
    """Affiche la ligne de résultat d'un fichier."""
    if r.erreur:
        print(f"  {ROUGE}✗{RESET} {r.nom:<24} {GRIS}{r.erreur}{RESET}")
        return

    if r.est_propre:
        ok = r.faux_positifs == 0
        marque = f"{VERT}✓{RESET}" if ok else f"{ROUGE}✗{RESET}"
        detail = "aucun faux positif" if ok else f"{r.faux_positifs} faux positif(s)"
        couleur = VERT if ok else ROUGE
        print(f"  {marque} {r.nom:<24} {couleur}{detail}{RESET}")
        return

    complet = not r.manquants
    marque = f"{VERT}✓{RESET}" if complet else f"{ORANGE}~{RESET}"
    extra = f"  {GRIS}(+{r.hors_corpus} hors corpus){RESET}" if r.hors_corpus else ""
    print(f"  {marque} {r.nom:<24} {len(r.trouves)}/{r.nb_attendus} attendues{extra}")

    for manquant in r.manquants:
        print(f"      {GRIS}manque : {manquant}{RESET}")


def afficher_synthese(resultats: list[Resultat]) -> bool:
    """
    Affiche le rappel et la précision.

    Returns:
        True si les deux seuils sont atteints.
    """
    trouves = sum(len(r.trouves) for r in resultats)
    attendus = sum(r.nb_attendus for r in resultats)
    faux_positifs = sum(r.faux_positifs for r in resultats)
    fichiers_propres = sum(1 for r in resultats if r.est_propre and not r.erreur)

    rappel = trouves / attendus if attendus else 1.0
    couleur_fp = VERT if faux_positifs == 0 else ROUGE

    print()
    print(f"  {GRAS}Rappel{RESET}          {rappel:>4.0%}   {GRIS}{trouves}/{attendus} erreurs attendues détectées{RESET}")
    print(f"  {GRAS}Faux positifs{RESET}  {couleur_fp}{faux_positifs:>5}{RESET}   {GRIS}sur {fichiers_propres} fichier(s) volontairement propre(s){RESET}")
    print()

    conforme = rappel >= SEUIL_RAPPEL and faux_positifs <= MAX_FAUX_POSITIFS
    if conforme:
        print(f"  {VERT}{GRAS}Configuration conforme{RESET} {GRIS}— rappel ≥ {SEUIL_RAPPEL:.0%}, aucun faux positif{RESET}")
    else:
        print(f"  {ROUGE}{GRAS}Configuration non conforme{RESET} {GRIS}— seuils : rappel ≥ {SEUIL_RAPPEL:.0%}, 0 faux positif{RESET}")
    print()
    return conforme


# ── Point d'entrée ────────────────────────────────────────────

def main() -> int:
    parseur = argparse.ArgumentParser(description="Banc d'essai SkillPath")
    parseur.add_argument("--url", default=URL_DEFAUT, help="URL de l'instance SkillPath")
    parseur.add_argument("--fichier", help="N'évaluer qu'un seul fichier du corpus")
    parseur.add_argument("--json", help="Écrire les résultats bruts dans un fichier JSON")
    args = parseur.parse_args()

    corpus = charger_attendus(ATTENDUS)
    if args.fichier:
        corpus = [f for f in corpus if f["nom"] == args.fichier]
        if not corpus:
            print(f"{ROUGE}Fichier absent du corpus : {args.fichier}{RESET}")
            return 1

    print(f"\n{GRAS}SkillPath — banc d'essai{RESET}")
    print(f"{GRIS}{len(corpus)} fichier(s) · {args.url}{RESET}\n")

    resultats: list[Resultat] = []

    for entree in corpus:
        nom = entree["nom"]
        chemin = DOSSIER_FICHIERS / nom
        attendus = [Attendu(a["libelle"], a["mots_cles"]) for a in entree.get("attendus", [])]

        if not chemin.exists():
            r = Resultat(nom=nom, erreur=f"introuvable dans {DOSSIER_FICHIERS.name}/")
            resultats.append(r)
            afficher_resultat(r)
            continue

        try:
            detectees = scanner(args.url, chemin)
        except RuntimeError as exc:
            r = Resultat(nom=nom, erreur=str(exc))
            resultats.append(r)
            afficher_resultat(r)
            continue

        r = evaluer(nom, attendus, detectees)
        resultats.append(r)
        afficher_resultat(r)

    conforme = afficher_synthese(resultats)

    if args.json:
        Path(args.json).write_text(
            json.dumps([vars(r) for r in resultats], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"  {GRIS}Résultats écrits dans {args.json}{RESET}\n")

    return 0 if conforme else 1


if __name__ == "__main__":
    sys.exit(main())
