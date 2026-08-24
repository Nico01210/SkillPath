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
- **Marquer une erreur comme résolue** — depuis le scan ; l'erreur sort alors des compteurs et de la courbe de progression
- **Profil** — nom et métier visé, injectés dans le prompt d'analyse pour orienter les priorités de l'IA

---

## Stack technique

| Couche           | Technologie                                     |
| ---------------- | ----------------------------------------------- |
| Backend          | Python 3.12, FastAPI, Pydantic v2               |
| IA               | OpenAI GPT-4o(Structured Outputs)               |
| RAG              | ChromaDB, text-embedding-3-small                |
| Parsing PDF      | PyMuPDF (fitz)                                  |
| Base de données | SQLite                                          |
| Frontend         | HTML, CSS, JavaScript vanilla, Jinja2, Chart.js |
| Tests            | pytest                                          |

---

## Installation

### Prérequis

- **Python 3.12**
- Une clé API OpenAI ([platform.openai.com](https://platform.openai.com)) — **optionnelle** : sans clé, l'app démarre en mode mock (voir plus bas)

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

> Aucun compilateur C++ n'est nécessaire : `chromadb` est épinglé sur une version
> qui fournit des wheels pré-compilés (voir [Note ChromaDB / Windows](#note-chromadb--windows)).

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
OPENAI_MODEL=gpt-4o
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

`requirements.txt` épingle **`chromadb==1.5.9`**, qui fournit des **wheels pré-compilés** :
`pip install -r requirements.txt` fonctionne sans outillage supplémentaire.

À éviter : les versions `0.4.x` dépendent de `chroma-hnswlib==0.7.3`, qui **n'a pas de wheel**
et doit être compilée — d'où l'erreur `Microsoft Visual C++ 14.0 or greater is required` sur
une machine sans les Microsoft C++ Build Tools.

Le code n'utilise que l'API stable (`PersistentClient`, `upsert`, `query`, `get`, `delete`),
il est donc compatible avec les deux lignées.

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
│       ├── rag_service.py        # Récupération des cours candidats
│       ├── rerank_service.py     # Tri LLM des candidats (« aucun » possible)
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
│   ├── test_schemas.py           # Tests signature d'erreur, profil
│   ├── test_llm_service.py       # Tests _parse_erreurs()
│   ├── test_pdf_service.py       # Tests decouper_en_chunks(), traiter_pdf()
│   ├── test_rag_service.py       # Tests titre_lisible()
│   ├── test_rapport_service.py   # Tests rapport_service
│   └── test_stats_service.py     # Tests stats_service
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

| Méthode   | Endpoint                     | Description                                                 |
| ---------- | ---------------------------- | ----------------------------------------------------------- |
| `GET`    | `/health`                  | Vérifie que le serveur tourne                              |
| `POST`   | `/import/`                 | Importe un PDF de cours                                     |
| `GET`    | `/import/liste`            | Liste les cours importés                                   |
| `GET`    | `/import/chunk`            | Récupère un extrait (chunk) d'un cours                    |
| `DELETE` | `/import/{nom_fichier}`    | Supprime un cours importé                                  |
| `POST`   | `/import/reimporter-tout`  | Réindexe tous les cours                                    |
| `POST`   | `/scan/`                   | Analyse un fichier de code                                  |
| `GET`    | `/rapport/`                | Rapport du jour                                             |
| `GET`    | `/rapport/hier`            | Rapport d'hier (pour les deltas)                            |
| `GET`    | `/rapport/dates`           | Liste des dates ayant un rapport                            |
| `GET`    | `/rapport/export`          | Export HTML du rapport                                      |
| `GET`    | `/stats/dashboard`         | Stats de progression (`?periode=semaine\|mois&offset=0\|1`) |
| `GET`    | `/resolutions/`            | Liste les erreurs marquées comme résolues                 |
| `PUT`    | `/resolutions/{signature}` | Marque une erreur comme résolue                            |
| `DELETE` | `/resolutions/{signature}` | Annule une résolution                                      |
| `GET`    | `/profil/`                 | Récupère le profil (métier visé, niveau)                |
| `PUT`    | `/profil/`                 | Met à jour le profil                                       |

Pages frontend : `/` (ou `/import-cours`), `/scan-code`, `/rapport-jour`, `/dashboard`.

---

## Tests

```bash
pytest tests/ -v
```

64 tests unitaires couvrant :

- `signature_erreur()` — stabilité de la signature d'une erreur d'un scan à l'autre
- `_parse_erreurs()` — parsing robuste du JSON LLM (backticks, JSON invalide, champs manquants)
- `decouper_en_chunks()` / `traiter_pdf()` — découpage PDF, PDF illisible, PDF sans texte
- `titre_lisible()` — libellé des extraits de cours (troncature, replis)
- `get_rapport_du_jour/hier()` — agrégation, déduplication des re-scans, échappement XSS
- `get_stats()` — agrégation SQL avec SQLite en mémoire, exclusion des erreurs résolues

---

## Variables d'environnement

| Variable           | Description         | Défaut                    |
| ------------------ | ------------------- | -------------------------- |
| `OPENAI_API_KEY` | Clé API OpenAI     | `""` (mode mock si vide) |
| `OPENAI_MODEL`   | Modèle OpenAI      | `gpt-4o`                 |
| `CHROMA_DB_PATH` | Chemin ChromaDB     | `data/chromadb`          |
| `SQLITE_DB_PATH` | Chemin SQLite       | `data/coach.db`          |
| `UPLOADS_PATH`   | Chemin uploads      | `data/uploads`           |
| `REPORTS_PATH`   | Chemin exports HTML | `data/reports`           |

> Les chemins sont calculés automatiquement à partir de la racine du projet.
> Ne les définis dans `.env` que pour stocker les données ailleurs, avec des **chemins absolus**.

---

## Comment une erreur est suivie dans le temps

Une erreur est identifiée par une **signature** = `sha1(fichier | ligne | niveau)`.
Le titre est volontairement **exclu** du calcul : c'est du texte libre généré par le LLM,
reformulé d'un scan à l'autre (« Injection SQL potentielle » / « Injection SQL possible »).
L'inclure faisait perdre l'état « résolu » à chaque re-scan.

Conséquences visibles :

- re-scanner le même fichier dans la journée **ne duplique pas** les cartes du rapport ;
- marquer une erreur résolue la **retire** du dashboard (compteurs et courbe) ;
- dans le Top 3, `occurrences` compte le **nombre de jours** où l'erreur a été détectée,
  pas le nombre de scans.

---

## Qualité de la recherche de cours (RAG)

La pertinence dépend directement du **texte extractible** des PDF importés :

- un cours **rédigé** (paragraphes) donne de bons résultats ;
- un cours composé de **captures d'écran ou de slides images** produit très peu de texte
  extractible : l'import est refusé en 422 s'il ne produit aucun chunk.

Une notion **absente du corpus** ne peut pas être rattachée : les erreurs concernées
affichent « Aucun cours lié », ce qui est le comportement voulu. Pour qu'un cours soit
exploitable, chaque notion doit occuper une section de 150-200 mots (l'ordre de grandeur d'un
chunk) dont le corps répète le nom de la notion — un titre seul se perd, car le découpage
ignore la mise en page.

Les embeddings sont produits par **`text-embedding-3-small`** (OpenAI, multilingue),
configurable via `EMBEDDING_MODEL`. Sans clé API, `chroma_service` retombe sur le modèle
local `all-MiniLM-L6-v2` afin que le mode MOCK fonctionne hors-ligne — mais celui-ci est
anglophone et discrimine mal des cours en français.

Le nom de la collection ChromaDB **porte le modèle d'embedding** (`cours__<modèle>`) : deux
modèles ne partagent ni la dimension des vecteurs ni le même espace sémantique, les mélanger
donnerait des recherches absurdes. Changer `EMBEDDING_MODEL` ouvre donc une collection vide —
l'app affiche « 0 cours indexé » jusqu'à un `POST /import/reimporter-tout`.

### Récupération large, puis tri par le LLM

Le rattachement d'une erreur à ses cours se fait en **deux étages** :

1. **Récupération** — ChromaDB ramène jusqu'à `RECALL_N` (20) candidats au-dessus d'un
   plancher bas, `RECALL_THRESHOLD` (0.32) ;
2. **Tri** — `rerank_service` demande au LLM, en **un seul appel pour tout le fichier**,
   quels extraits traitent réellement la notion en jeu, avec « aucun » comme réponse
   légitime.

Ce second étage n'est pas un raffinement : la similarité vectorielle seule **ne peut pas**
faire ce tri, et ce n'est pas une question de réglage. Mesuré sur les cours de test, une
erreur *sans* cours correspondant dans l'index (injection SQL, avant l'import d'un cours de
sécurité) scorait **0.461**, quand un vrai match (`open()` sans `with` → cours sur les
exceptions) plafonnait à **0.458**. Le bruit score plus haut que le signal : tout seuil
unique garde forcément du faux ou jette du vrai. La similarité mesure une proximité de
vocabulaire — « requête », « malveillant », « sécurité » rapprochent mécaniquement
l'injection SQL d'un cours REST/GraphQL.

La fenêtre de récupération est large pour la même raison : sur une erreur « pas de type
hints », le chunk intitulé « Absence de type hints (Python) » sortait au **rang 16** (0.437),
derrière un passage sur le God Object (0.517). On ne peut pas faire confiance au top 8 du
classement vectoriel, donc on soumet largement et c'est le tri qui décide.

Le tri procède en deux temps par erreur, imposés par le schéma de réponse : il **nomme
d'abord** la notion à revoir (« requêtes SQL paramétrées »), puis juge chaque extrait contre
cette notion nommée. Sans cet ancrage, le modèle jugeait « est-ce le même domaine ? » et
retenait un passage « Sécurité : rate limit, CORS » pour une injection SQL.

Mesuré sur un lot réel de 4 erreurs, 6 exécutions : **6/6 corrects** sur les quatre, y compris
« Aucun cours lié » pour une notion absente du corpus. Avant l'import du cours de sécurité,
l'injection SQL était rattachée à tort dans 2 cas sur 6 — c'est le signe qu'une notion non
couverte reste le point faible du tri, et qu'importer le cours manquant vaut mieux que
durcir le prompt.

Coût : un appel `OPENAI_MODEL` supplémentaire par scan, de l'ordre de 10k tokens en entrée.
`MAX_EXTRAITS_ENVOYES` (60) plafonne le nombre d'extraits distincts soumis ; au-delà, les
moins bien classés sont écartés **avec un log**, pour qu'une coupe ne passe jamais pour une
couverture complète. Si le tri échoue (pas de
clé API, panne réseau, réponse tronquée), `rag_service` retombe sur un filtrage par
`FALLBACK_THRESHOLD` (0.42) : dégradé — il laisse passer des rattachements faux — mais un
tri indisponible ne fait jamais échouer un scan.

Les seuils sont **étalonnés sur ce couple modèle d'embedding + `CHUNK_SIZE`** ; ils n'ont
aucune valeur absolue et doivent être remesurés si l'un des deux change.

---

## Limitations connues (V2)

- Application mono-utilisateur locale — pas d'authentification
- Import PDF un fichier à la fois
- Scanne de plusieurs fichiers de code (dossier .zip ou repo entier)
- Le titre d'un extrait de cours est un aperçu de son contenu, pas un vrai titre de chapitre
  (le chunking aplatit la mise en page du PDF)
- Sans clé API, les embeddings retombent sur un modèle local anglophone (voir ci-dessus)
- Le dashboard est une fenêtre glissante de 7 ou 30 jours ; l'`offset` (période précédente)
  existe côté API mais n'est pas exposé dans l'interface
- Pas de tests d'intégration (ChromaDB, OpenAI)

---

## Auteur

Projet réalisé dans le cadre d'une formation en reconversion professionnelle — **Nico**
GitHub : [github.com/Nico01210/SkillPath](https://github.com/Nico01210/SkillPath)
