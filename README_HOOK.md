# Revue automatique au push — hook Git

SkillPath peut relire le code modifié avant chaque `git push`, sans quitter le terminal. Le développeur reçoit les erreurs détectées et les chapitres de cours correspondants au moment où il pousse son travail.

---

## Installation

Depuis la racine du dépôt à surveiller :

```bash
# 1. Installer le hook
cp scripts/pre-push .git/hooks/pre-push
chmod +x .git/hooks/pre-push

# 2. Installer la configuration
cp scripts/.skillpath.yml .skillpath.yml
```

SkillPath doit tourner pendant le push :

```bash
uvicorn main:app
```

Aucune dépendance à installer : le hook n'utilise que la bibliothèque standard Python.

---

## Configuration

Le fichier `.skillpath.yml` à la racine du dépôt pilote le comportement.

| Clé | Valeurs | Effet |
|---|---|---|
| `url` | URL | Instance SkillPath à appeler |
| `mode` | `auto` / `manuel` / `off` | Déclenchement de la revue |
| `extensions` | liste | Types de fichiers analysés |
| `ignore` | liste | Chemins exclus |
| `bloquer_si_critique` | `true` / `false` | Refuser le push en cas d'erreur critique |
| `max_fichiers` | entier | Plafond du nombre d'appels par push |

### Les trois modes

**`auto`** — la revue se lance à chaque push.

```bash
git push
```

**`manuel`** — la revue ne se lance que sur demande explicite. Le développeur décide quand son code est prêt à être relu.

```bash
SKILLPATH=1 git push    # avec revue
git push                # sans revue
```

**`off`** — le hook ne fait rien. Permet de désactiver temporairement sans désinstaller.

---

## Fonctionnement

1. Git déclenche le hook avant l'envoi des commits
2. Le hook interroge Git sur les fichiers ajoutés ou modifiés depuis le dernier push
3. Il filtre selon `extensions` et `ignore`, puis plafonne à `max_fichiers`
4. Chaque fichier retenu est envoyé à `POST /scan` de l'instance SkillPath
5. Les erreurs et les cours associés s'affichent dans le terminal
6. Le push est refusé uniquement si `bloquer_si_critique` est actif et qu'une erreur critique a été détectée

### Exemple de sortie

```
SkillPath — revue de 2 fichier(s)

  backend/services/auth.py — 1 critique(s) · 2 avertissement(s)
    CRITIQUE  Requête SQL non paramétrée  ligne 42
      La requête construit du SQL par concaténation — risque d'injection.
      → à relire : securite_applicative — chunk 0
    AVERTISSEMENT  Exception trop générique  ligne 71
      Le bloc except masque les vraies erreurs et complique le débogage.
      → à relire : erreurs_exceptions — chunk 2

  OK  backend/models/schemas.py — aucun problème détecté
```

---

## Principes de conception

**Le hook ne bloque jamais par accident.** Si SkillPath n'est pas lancé, si le fichier de configuration est absent, ou si le script lève une exception, le push passe. Un outil de revue qui empêche de travailler est désinstallé le jour même.

**Le blocage est un choix explicite.** Seul `bloquer_si_critique: true` refuse un push, et uniquement sur des erreurs de niveau critique. L'échappatoire standard de Git reste disponible :

```bash
git push --no-verify
```

**Aucune dépendance externe.** Le hook n'utilise que `urllib`, `subprocess` et `json` de la bibliothèque standard. Un hook qui exigerait un `pip install` avant de fonctionner ne serait jamais adopté. Le parseur de configuration est volontairement minimal — le format étant plat, PyYAML n'est pas nécessaire.

**Le nombre d'appels est plafonné.** `max_fichiers` évite qu'un commit de refactoring déclenche des dizaines d'appels à l'API.

---

## Limite actuelle

Le hook s'exécute sur la machine du développeur, où SkillPath tourne déjà en local. C'est ce qui rend l'intégration possible sans aucune infrastructure.

Un runner de CI, lui, s'exécute sur une machine distante qui ne peut pas joindre le `localhost` du développeur. Automatiser la revue dans une pipeline suppose donc une instance SkillPath accessible sur le réseau — ce qui sort du périmètre actuel, défini comme une application locale mono-utilisateur.

---

## Évolution V2 — GitHub Actions

Une fois l'application hébergée, le même mécanisme devient un job de pipeline. Le workflow ci-dessous est fourni à titre de cible : il n'est pas fonctionnel tant qu'aucune instance n'est déployée.

```yaml
# .github/workflows/skillpath.yml
name: Revue de code SkillPath

on:
  # Déclenchement automatique sur les pull requests
  pull_request:
    types: [opened, synchronize]
  # Déclenchement manuel depuis l'onglet Actions
  workflow_dispatch:

jobs:
  revue:
    runs-on: ubuntu-latest

    steps:
      - name: Récupérer le code
        uses: actions/checkout@v4
        with:
          # Historique complet : nécessaire pour diffuser la base de comparaison
          fetch-depth: 0

      - name: Installer Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Analyser les fichiers modifiés
        env:
          # L'URL de l'instance hébergée, stockée en secret du dépôt
          SKILLPATH_URL: ${{ secrets.SKILLPATH_URL }}
        run: python scripts/ci_review.py --base origin/${{ github.base_ref }}
```

### Ce qui reste à faire pour la V2

| Chantier | Détail |
|---|---|
| Héberger SkillPath | Instance accessible depuis les runners GitHub |
| Authentifier les appels | Jeton d'API, pour éviter un endpoint public ouvert |
| Adapter le script | Comparer contre `origin/main` plutôt que `@{push}` |
| Commenter la pull request | Publier les erreurs via l'API GitHub plutôt qu'en logs |
| Scan en lot | Un appel par fichier reste coûteux sur une grosse PR |

Le déclenchement `workflow_dispatch` correspond au mode `manuel` du hook local : le développeur lance la revue d'un clic depuis l'interface GitHub quand il estime son code prêt.
