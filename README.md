# SkillPath — Coach IA pour étudiant en reconversion

> Analyse ton code, détecte les erreurs, et te renvoie vers tes propres cours PDF.

SkillPath est une application web locale mono-utilisateur qui combine l'analyse de code par IA (OpenAI) et la recherche sémantique dans tes cours (RAG + ChromaDB) pour te donner un feedback personnalisé ancré dans ta formation.

---

## Fonctionnalités

- **Import de cours PDF** — découpe automatiquement tes cours en chunks et les vectorise dans ChromaDB
- **Scanner du code** — analyse un fichier de code (.py, .js, .ts, .java...) via OpenAI et détecte les erreurs avec leur niveau de gravité
- **Recommandations RAG** — croise chaque erreur avec tes cours importés et pointe vers les chapitres pertinents
- **Rapport journalier** — synthèse de toutes les analyses du jour avec export HTML, comparaison avec la veille
- **Dashboard de progression** — courbe d'évolution sur 7 ou 30 jours, top 3 erreurs récurrentes, top 3 cours recommandés, deltas vs période précédente
- **Marquer une erreur comme résolue** — depuis le scan, et suivi des résolutions
- **Profil** — métier visé / niveau, pour adapter le prompt d'analyse

---

## Stack technique

| Couche           | Technologie                                     |
| ---------------- | ----------------------------------------------- |
| Backend          | Python 3.12, FastAPI, Pydantic v2               |
| IA               | OpenAI GPT-4o-mini (Structured Outputs)         |
| RAG              | ChromaDB, all-MiniLM-L6-v2                      |
| Parsing PDF      | PyMuPDF (fitz)                                  |
| Base de données | SQLite                                          |
| Frontend         | HTML, CSS, JavaScript vanilla, Jinja2, Chart.js |
| Tests            | pytest                                          |

---

## Installation

### Prérequis

- **Python 3.12**
- Une clé API OpenAI ([platform.openai.com](https://platform.openai.com)) — **optionnelle** : sans clé, l'app démarre en mode mock (voir plus bas)
- **Windows uniquement** : selon la version de `chromadb` installée, un compilateur C++ peut être requis — voir [Note ChromaDB / Windows](#note-chromadb--windows).

### 1. Cloner le projet

```bash
git clone https://github.com/Nico01210/SkillPath
cd SkillPath
```

### 2. Créer et activer le venv

```bash
python -m venv .venv

# Linux / macOS
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

> **Windows sans Visual C++ Build Tools** : si l'installation échoue sur `chroma-hnswlib`
> (`Microsoft Visual C++ 14.0 or greater is required`), voir la
> [Note ChromaDB / Windows](#note-chromadb--windows) ci-dessous.

### 4. Créer le dossier de données

L'app stocke sa base SQLite, l'index ChromaDB, les PDF importés et les rapports dans `data/`.
Ce dossier est **gitignoré** (donc absent après un clone) : crée-le avant le premier lancement.

```bash
# Linux / macOS
mkdir -p data/chromadb data/uploads data/reports

# Windows (PowerShell)
mkdir data\chromadb, data\uploads, data\reports
```

### 5. Configurer l'environnement

Copie le fichier d'exemple et remplis tes valeurs :

```bash
cp .env.example .env
```

```env
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-4o-mini
```

> Sans clé API (ou `OPENAI_API_KEY` vide), l'app démarre en **mode mock** — des erreurs fictives
> sont retournées pour tester le pipeline complet sans coût ni appel réseau.
> Les chemins (`data/...`) sont calculés automatiquement ; ne les surcharge dans `.env`
> qu'avec des chemins **absolus** (voir `.env.example`).

### 6. Lancer l'application

```bash
uvicorn main:app --reload
```

Ouvre [http://localhost:8000](http://localhost:8000) dans ton navigateur.

---

## Note ChromaDB / Windows

`requirements.txt` épingle `chromadb==0.4.24`, qui dépend de `chroma-hnswlib==0.7.3`.
Cette version **n'a pas de wheel pré-compilé** : `pip` doit la **compiler**, ce qui nécessite
les **Microsoft C++ Build Tools**. Sur une machine qui les a déjà (souvent installés avec
Visual Studio), l'installation passe sans rien faire de plus.

Si ce n'est pas ton cas, deux options :

- **A — Installer une version récente de ChromaDB (recommandé, sans compilateur)**
  Les versions récentes fournissent des binaires prêts à l'emploi. Le code n'utilise
  que l'API stable (`PersistentClient`, `upsert`, `query`...), donc aucun changement de code.

  ```bash
  pip install fastapi==0.111.0 "uvicorn[standard]==0.29.0" python-multipart==0.0.9 \
    openai==1.109.1 pymupdf==1.24.9 python-dotenv==1.0.1 \
    pydantic==2.7.1 pydantic-settings==2.3.0 chromadb --only-binary=:all:
  ```

- **B — Installer les Microsoft C++ Build Tools** pour garder `chromadb==0.4.24` tel quel
  ([télécharger](https://visualstudio.microsoft.com/visual-cpp-build-tools/)), puis relancer
  `pip install -r requirements.txt`.

---

## Utilisation

### Étape 1 — Importer tes cours

Depuis la page **Import cours**, glisse un PDF de cours. Il est découpé en chunks et vectorisé dans ChromaDB.

### Étape 2 — Scanner du code

Depuis la page **Scanner du code**, glisse un fichier de code. L'IA analyse les erreurs et les croise avec tes cours importés.

### Étape 3 — Consulter le rapport

La page **Rapport du jour** agrège toutes les analyses de la journée avec des statistiques et un export HTML.

### Étape 4 — Suivre ta progression

La page **Ma progression** affiche une courbe d'évolution sur 7 ou 30 jours ainsi que le top 3 des erreurs récurrentes et des cours recommandés.

---

## Structure du projet

```
SkillPath/
├── backend/
│   ├── config.py                 # Configuration (clé API, chemins)
│   ├── models/
│   │   └── schemas.py            # Modèles Pydantic
│   ├── routers/
│   │   ├── import_router.py      # /import (upload, liste, chunk, suppression, réimport)
│   │   ├── scan_router.py        # /scan
│   │   ├── rapport_router.py     # /rapport (jour, hier, dates, export)
│   │   ├── stats_router.py       # /stats/dashboard
│   │   ├── resolutions_router.py # /resolutions (marquer résolu / lister / annuler)
│   │   └── profil_router.py      # /profil (lecture / mise à jour)
│   └── services/
│       ├── pdf_service.py        # Parsing et chunking PDF
│       ├── chroma_service.py     # Embeddings et recherche vectorielle
│       ├── rag_service.py        # Recherche de cours pertinents
│       ├── llm_service.py        # Analyse de code via OpenAI
│       ├── sqlite_service.py     # Persistance des analyses
│       ├── rapport_service.py    # Génération du rapport journalier
│       ├── stats_service.py      # Agrégation des statistiques
│       └── upload_utils.py       # Utilitaires d'upload de fichiers
├── frontend/
│   ├── static/
│   │   ├── style.css             # Design system global
│   │   └── js/                   # Scripts front (vanilla)
│   └── templates/
│       ├── base.html             # Layout commun (sidebar, nav)
│       ├── import.html           # Page import cours
│       ├── scan.html             # Page scanner du code
│       ├── rapport.html          # Page rapport journalier
│       └── dashboard.html        # Page dashboard progression
├── tests/
│   ├── test_llm_service.py       # Tests _parse_erreurs()
│   ├── test_pdf_service.py       # Tests decouper_en_chunks()
│   ├── test_rapport_service.py   # Tests rapport_service
│   └── test_stats_service.py    # Tests stats_service
├── data/                         # Données locales (gitignorées — à créer, voir étape 4)
│   ├── chromadb/                 # Base vectorielle
│   ├── coach.db                  # Base SQLite (créée au 1er lancement)
│   ├── uploads/                  # PDFs importés
│   └── reports/                  # Rapports HTML exportés
├── main.py                       # Point d'entrée FastAPI
├── requirements.txt
├── .env.example
└── .env                          # Variables d'environnement (non commité)
```

---

## API — Endpoints principaux

Toutes les routes API sont documentées et testables sur [http://localhost:8000/docs](http://localhost:8000/docs).

| Méthode  | Endpoint                    | Description                                                 |
| -------- | --------------------------- | ----------------------------------------------------------- |
| `GET`    | `/health`                   | Vérifie que le serveur tourne                               |
| `POST`   | `/import/`                  | Importe un PDF de cours                                     |
| `GET`    | `/import/liste`             | Liste les cours importés                                    |
| `GET`    | `/import/chunk`             | Récupère un extrait (chunk) d'un cours                      |
| `DELETE` | `/import/{nom_fichier}`     | Supprime un cours importé                                   |
| `POST`   | `/import/reimporter-tout`   | Réindexe tous les cours                                     |
| `POST`   | `/scan/`                    | Analyse un fichier de code                                  |
| `GET`    | `/rapport/`                 | Rapport du jour                                             |
| `GET`    | `/rapport/hier`             | Rapport d'hier (pour les deltas)                            |
| `GET`    | `/rapport/dates`            | Liste des dates ayant un rapport                            |
| `GET`    | `/rapport/export`           | Export HTML du rapport                                      |
| `GET`    | `/stats/dashboard`          | Stats de progression (`?periode=semaine\|mois&offset=0\|1`) |
| `GET`    | `/resolutions/`             | Liste les erreurs marquées comme résolues                   |
| `PUT`    | `/resolutions/{signature}`  | Marque une erreur comme résolue                             |
| `DELETE` | `/resolutions/{signature}`  | Annule une résolution                                       |
| `GET`    | `/profil/`                  | Récupère le profil (métier visé, niveau)                    |
| `PUT`    | `/profil/`                  | Met à jour le profil                                        |

Pages frontend : `/` (ou `/import-cours`), `/scan-code`, `/rapport-jour`, `/dashboard`.

---

## Tests

```bash
pytest tests/ -v
```

33 tests unitaires couvrant :

- `_parse_erreurs()` — parsing robuste du JSON LLM (backticks, JSON invalide, champs manquants)
- `decouper_en_chunks()` — découpage PDF (taille, chevauchement, structure)
- `get_rapport_du_jour/hier()` — agrégation des analyses + échappement XSS
- `get_stats()` — agrégation SQL avec SQLite en mémoire

---

## Variables d'environnement

| Variable           | Description         | Défaut                    |
| ------------------ | ------------------- | -------------------------- |
| `OPENAI_API_KEY` | Clé API OpenAI     | `""` (mode mock si vide) |
| `OPENAI_MODEL`   | Modèle OpenAI      | `gpt-4o-mini`            |
| `CHROMA_DB_PATH` | Chemin ChromaDB     | `data/chromadb`          |
| `SQLITE_DB_PATH` | Chemin SQLite       | `data/coach.db`          |
| `UPLOADS_PATH`   | Chemin uploads      | `data/uploads`           |
| `REPORTS_PATH`   | Chemin exports HTML | `data/reports`           |

> Les chemins sont calculés automatiquement à partir de la racine du projet.
> Ne les définis dans `.env` que pour stocker les données ailleurs, avec des **chemins absolus**.

---

## Limitations connues (V2)

- Application mono-utilisateur locale — pas d'authentification
- Import PDF un fichier à la fois
- Les titres de cours recommandés affichent le nom du chunk (`cours.pdf — chunk 2`) plutôt qu'un titre lisible
- Pas de tests d'intégration (ChromaDB, OpenAI)

---

## Auteur

Projet réalisé dans le cadre d'une formation en reconversion professionnelle — **Nico**
GitHub : [github.com/Nico01210/SkillPath](https://github.com/Nico01210/SkillPath)
