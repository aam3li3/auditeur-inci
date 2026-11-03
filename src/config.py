"""Paramètres du projet : chemins des fichiers et adresse du modèle.

Rien de secret ici : la clé d'API éventuelle est lue dans une variable
d'environnement au moment de l'exécution (exigence R1 : aucune clé dans le dépôt).
"""
import os
from pathlib import Path

# Dossier principal du projet (le dossier qui contient src/)
RACINE = Path(__file__).resolve().parent.parent

# Données
DOSSIER_REFERENCE = RACINE / "data" / "reference"
FICHIER_BRUT = RACINE / "data" / "brut" / "produits_bruts.csv.gz"
FICHIER_PROPRE = RACINE / "data" / "propre" / "produits.csv"
FICHIER_JOURNAL = RACINE / "data" / "journal_nettoyage.md"

# Résultats
DOSSIER_RESULTATS = RACINE / "evaluation" / "resultats"
FICHIER_MODELE = DOSSIER_RESULTATS / "classifieur.joblib"
FICHIER_TACHES = RACINE / "evaluation" / "taches.jsonl"

# Modèle de langage. Par défaut : llama-server sur le port 8080 (voir README).
#   Ollama   : LLM_URL=http://localhost:11434/v1  LLM_MODELE=qwen3.5:4b-q4_K_M
#   Cerebras : LLM_URL=https://api.cerebras.ai/v1 LLM_MODELE=qwen-3.8-27b LLM_CLE=<votre clé> LLM_PAUSE=13
LLM_URL = os.environ.get("LLM_URL", "http://localhost:8080/v1")
LLM_MODELE = os.environ.get("LLM_MODELE", "qwen3.5-4b")
LLM_CLE = os.environ.get("LLM_CLE")  # vide en local : llama-server n'en demande pas
LLM_PAUSE = float(os.environ.get("LLM_PAUSE", "0"))  # secondes d'attente minimum entre deux appels
LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.7"))  # > 0, sinon les 3 lancements seraient identiques
LLM_REFLEXION = os.environ.get("LLM_REFLEXION", "non") == "oui"  # mode « thinking » de Qwen : désactivé par défaut
