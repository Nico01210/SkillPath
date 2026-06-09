# Coach IA

Application web locale qui analyse ton code, identifie tes lacunes et te renvoie vers les cours pertinents.

## Stack

* **Backend** : Python 3.11 + FastAPI
* **IA** : OpenAI API (GPT-4o Mini)
* **RAG** : ChromaDB (base vectorielle locale)
* **BDD** : SQLite (historique des analyses)
* **Frontend** : HTML + CSS + JS vanilla

## Installation

bash

```bash
# 1. Cloner le projet
git clone ...
cd coach_ia

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
coach_ia/
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
