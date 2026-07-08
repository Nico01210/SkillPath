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
- **Feature "Marquer comme résolue"** — marque une erreur comme résolue directement depuis le scan

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

- Python 3.12
- Une clé API OpenAI ([platform.openai.com](https://platform.openai.com))

### 1. Cloner le projet

```bash
git clone https://github.com/Nico01210/SkillPath
cd SkillPath
```

### 2. Créer et activer le venv

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# ou
.venv\Scripts\activate     # Windows
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Configurer l'environnement

Crée un fichier `.env` à la racine :

```env
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-4o-mini
```

Sans clé API, l'app démarre en **mode mock** — des erreurs fictives sont retournées pour tester le pipeline sans coût.

### 5. Lancer l'application

```bash
uvicorn main:app --reload
```

Ouvre [http://localhost:8000](http://localhost:8000) dans ton navigateur.

---

## Utilisation

### Étape 1 — Importer tes cours

Depuis la page **Import cours**, glisse un PDF de cours (max 10 Mo). Il est découpé en chunks et vectorisé dans ChromaDB.

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
│   ├── config.py               # Configuration (clé API, chemins)
│   ├── models/
│   │   └── schemas.py          # Modèles Pydantic
│   ├── routers/
│   │   ├── import_router.py    # POST /import
│   │   ├── scan_router.py      # POST /scan
│   │   ├── rapport_router.py   # GET /rapport, GET /rapport/hier
│   │   └── stats_router.py     # GET /stats/dashboard
│   └── services/
│       ├── pdf_service.py      # Parsing et chunking PDF
│       ├── chroma_service.py   # Embeddings et recherche vectorielle
│       ├── rag_service.py      # Recherche de cours pertinents
│       ├── llm_service.py      # Analyse de code via OpenAI
│       ├── sqlite_service.py   # Persistance des analyses
│       ├── rapport_service.py  # Génération du rapport journalier
│       └── stats_service.py    # Agrégation des statistiques
├── frontend/
│   ├── static/
│   │   └── style.css           # Design system global
│   └── templates/
│       ├── base.html           # Layout commun (sidebar, nav)
│       ├── import.html         # Page import cours
│       ├── scan.html           # Page scanner du code
│       ├── rapport.html        # Page rapport journalier
│       └── dashboard.html      # Page dashboard progression
├── tests/
│   ├── test_llm_service.py     # Tests _parse_erreurs()
│   ├── test_pdf_service.py     # Tests decouper_en_chunks()
│   ├── test_rapport_service.py # Tests rapport_service
│   └── test_stats_service.py  # Tests stats_service
├── data/                       # Données locales (gitignorées)
│   ├── chromadb/               # Base vectorielle
│   ├── uploads/                # PDFs importés
│   └── reports/                # Rapports HTML exportés
├── main.py                     # Point d'entrée FastAPI
├── requirements.txt
└── .env                        # Variables d'environnement (non commité)
```

---

## API — Endpoints principaux

| Méthode | Endpoint             | Description                                                 |
| -------- | -------------------- | ----------------------------------------------------------- |
| `POST` | `/import/`         | Import un PDF de cours                                      |
| `GET`  | `/import/liste`    | Liste les cours importés                                   |
| `POST` | `/scan/`           | Analyse un fichier de code                                  |
| `GET`  | `/rapport/`        | Rapport du jour                                             |
| `GET`  | `/rapport/hier`    | Rapport d'hier (pour les deltas)                            |
| `GET`  | `/rapport/export`  | Export HTML du rapport                                      |
| `GET`  | `/stats/dashboard` | Stats de progression (`?periode=semaine\|mois&offset=0\|1`) |

Documentation interactive disponible sur [http://localhost:8000/docs](http://localhost:8000/docs).

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

# SkillPath

Application web locale qui analyse ton code, identifie tes lacunes, te renvoie vers les cours pertinents et fait un suivi de ta progression.

## Stack

* **Backend** : Python 3.11 + FastAPI
* **IA** : OpenAI API (GPT-4o Mini)
* **RAG** : ChromaDB (base vectorielle locale)
* **BDD** : SQLite (historique des analyses)
* **Frontend** : HTML + CSS + JS vanilla

## Installation

```bash
# 1. Cloner le projet
git clone ...
cd SkillPath

# 2. Créer l'environnement virtuel
python -m venv .venv
source .venv/bin/activate      # Mac/Linux
# .venv\Scripts\activate       # Windows

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Configurer les variables d'environnement
cp .env.example .env
# Ouvre .env et colle ta clé OpenAI

# 5. Lancer le serveur
uvicorn main:app --reload
```

## Accès

* App : [http://localhost:8000](http://localhost:8000)
* Docs API (auto-générées) : [http://localhost:8000/docs](http://localhost:8000/docs)

## Structure

```
SkillPath/
├── main.py                  # Point d'entrée FastAPI
├── requirements.txt
├── .env.example
├── backend/
│   ├── config.py            # Variables d'environnement
│   ├── routers/             # Endpoints : import, scan, rapport
│   ├── services/            # Logique métier : RAG, LLM, PDF, SQLite
│   └── models/              # Schémas Pydantic (validation des données)
├── frontend/
│   ├── static/              # CSS, JS
│   └── templates/           # HTML
└── data/
    ├── chromadb/            # Base vectorielle (gitignorée)
    ├── uploads/             # PDFs importés (gitignorés)
    └── reports/             # Rapports HTML exportés (gitignorés)
```
