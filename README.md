# Auditeur INCI : un copilote de transparence des ingrédients cosmétiques

Projet final — Coding for AI & Data Science (aivancity, PGE3, 2026–2027).

On donne au système un produit cosmétique (ou sa liste d'ingrédients INCI) et les allergies d'une utilisatrice.
Il lit la liste, repère les allergènes de parfum à déclarer selon la réglementation européenne et les perturbateurs
endocriniens potentiels, et dit si le produit est compatible avec les allergies déclarées.

Le modèle de langage (Qwen3.5-4B) ne lit pas les listes lui-même : il appelle des outils écrits en Python. Et
le code lui interdit de déclarer « compatible » un produit qui contient un allergène de l'utilisatrice, même si
on le lui demande. On mesure ensuite ce que ces outils et cette barrière apportent par rapport au même modèle seul.

```
question ──► agent.py (boucle) ──► Qwen3.5-4B (llama-server)
                 │   ▲                  │ demande un outil
                 │   └── résultat ◄─────┘
                 ▼
            outils.py (brique 1) : chercher_produit · analyser_produit · analyser_inci
                 │                       │
            inci.py (lecture INCI)   classifieur.py (brique 7) sur data/propre/produits.csv (brique 6)
                 │
verdict final ──► garde.py (brique 3) : le produit contient l'allergène ? → verdict remplacé
```

| Brique | Ce qui la porte | Où |
|---|---|---|
| 1 — Votre propre outil | 3 outils écrits en Python, appelés par Qwen dans une boucle écrite à la main | `src/outils.py`, `src/agent.py` |
| 3 — Règle imposée par le code | jamais « COMPATIBLE » si le produit contient un allergène déclaré | `src/garde.py`, `tests/test_garde.py` |
| 6 — Données sales, décisions écrites | 22 878 listes INCI réelles, journal chiffré, règles tirées du règlement européen | `src/inci.py`, `src/nettoyage.py`, `data/journal_nettoyage.md` |
| 7 — Modèle appris sur des données | régression logistique « certifié bio ou non », testée sur des marques jamais vues | `src/classifieur.py`, `evaluation/evaluer_classifieur.py` |
| 9 — Comparaison mesurée | 12 tâches à réponse connue, système contre Qwen seul, 3 lancements | `evaluation/benchmark.py` |

Les preuves de chaque brique sont rassemblées dans [EVIDENCE.md](EVIDENCE.md).

## Modèle utilisé

**Qwen3.5-4B, quantifié Q4_K_M (`qwen3.5:4b-q4_K_M`), sur ma propre machine (MacBook Air), servi par Ollama**,
avec une longueur de contexte fixée à 16 384 tokens (réglage « Context length » d'Ollama). Le mode « réflexion »
(thinking) de Qwen est désactivé par le code (`LLM_REFLEXION`, voir plus bas). Les résultats d'EVIDENCE.md ont été
obtenus avec cette installation. llama-server fonctionne aussi (section « Lancer le modèle »).

## Installation (clone neuf)

Python 3.10 ou plus récent.

```bash
git clone <url-du-depot> auditeur-inci
cd auditeur-inci
python -m venv .venv
source .venv/bin/activate              # Windows : .venv\Scripts\activate
pip install -r requirements.txt
python -m pytest                       # R2 : 83 tests, sans modèle ni réseau (environ 2 s)
```

## Préparer les données et le classifieur (sans modèle de langage)

```bash
python -m src.nettoyage                # brique 6 : data/propre/produits.csv + data/journal_nettoyage.md (~1 min 30)
python -m evaluation.evaluer_classifieur   # brique 7 : evaluation/resultats/classifieur_certification.md (~2 s)
python -m evaluation.taches            # brique 9 : vérifie les 12 tâches figées de evaluation/taches.jsonl
```

Les données brutes sont fournies dans `data/brut/produits_bruts.csv.gz` (extrait de l'export Open Beauty Facts,
sans aucune colonne personnelle). Pour repartir de l'export complet : `python -m src.preparer_donnees --telecharger`
(la base change chaque jour : les chiffres peuvent alors varier un peu).

## Lancer le modèle

Dans un second terminal (fichier GGUF téléchargé au préalable, environ 3 Go) :

```bash
llama-server -m Qwen3.5-4B-Q4_K_M.gguf --port 8080 -c 16384 --jinja
```

`--jinja` est indispensable : c'est lui qui active les appels d'outils. Le code s'adresse par défaut à
`http://localhost:8080/v1`. Pour une autre installation, on change seulement des variables d'environnement :

| Installation | Variables à définir |
|---|---|
| Ollama | `LLM_URL=http://localhost:11434/v1` et `LLM_MODELE=qwen3.5:4b-q4_K_M` (après `ollama pull qwen3.5:4b-q4_K_M`) |
| Activer le mode « réflexion » de Qwen (désactivé par défaut) | `LLM_REFLEXION=oui` |
| Cerebras (si l'ordinateur ne fait pas tourner le 4B) | `LLM_URL=https://api.cerebras.ai/v1`, `LLM_MODELE=qwen-3.8-27b`, `LLM_CLE=<votre clé>`, `LLM_PAUSE=13` |

Aucune clé n'est écrite dans le dépôt : `LLM_CLE` est lue dans l'environnement au moment de l'exécution.

## Démonstration et benchmark (avec le modèle lancé)

```bash
python -m src.auditeur --chercher "shampooing"                                  # trouver un code (sans modèle)
python -m src.auditeur --code 3140100339604 --allergies linalool --piege --comparer
python -m evaluation.voir_trace evaluation/resultats/traces/demo_systeme.jsonl

python -m evaluation.benchmark --lancements 1 --limite 1    # essai rapide : 3 tâches
python -m evaluation.benchmark --lancements 3               # brique 9 complète : 72 exécutions
```

Durée du benchmark complet : 12 tâches × 2 modes × 3 lancements = 72 exécutions, soit environ 30 à 60 minutes en
local sur processeur.

## Structure

```
src/
  config.py            chemins et adresse du modèle (lue dans l'environnement)
  preparer_donnees.py  étape 0 : extraction de l'export Open Beauty Facts
  references.py        chargement des listes de référence
  inci.py              lecture d'une liste INCI : découpage, noms officiels, fautes corrigées
  nettoyage.py         brique 6 : nettoyage de tous les produits + journal
  classifieur.py       brique 7 : le modèle « certifié bio ou non »
  garde.py             brique 3 : la barrière de sécurité sur le verdict
  outils.py            brique 1 : les trois outils et leur description pour le modèle
  llm.py               client HTTP compatible OpenAI
  agent.py             la boucle d'agent et ses traces
  questions.py         les questions posées au modèle
  demarrage.py         chargement des données, du lecteur et du classifieur
  auditeur.py          la démonstration de soutenance
evaluation/
  evaluer_classifieur.py   brique 7
  taches.py                brique 9 : choix des tâches
  benchmark.py             brique 9 : système contre modèle seul
  voir_trace.py            lecture d'une trace
  resultats/               sorties (tableaux, prédictions, traces)
data/
  brut/                    extrait de l'export Open Beauty Facts
  reference/               listes officielles : CosIng, allergènes, perturbateurs potentiels, synonymes, certifications
tests/                     R2 : tests à réponse connue (pytest)
ai_log/                    R3 : journal d'usage de l'IA
```

## Données et sources

- **Produits** : [Open Beauty Facts](https://world.openbeautyfacts.org), licence Open Database License (ODbL),
  export `beauty.parquet` du 01/11/2026 (dépôt Hugging Face `openfoodfacts/product-database`). Les fichiers dérivés
  de cette base (`data/brut/`, `data/propre/`) sont partagés sous la même licence.
- **Noms INCI officiels** : base européenne CosIng (version de 2016 conservée dans le dépôt GitHub
  `openfoodfacts/openbeautyfacts`, dossier `cosing/`).
- **Allergènes à déclarer** : règlement (CE) n° 1223/2009, annexe III, complétée par le règlement (UE) 2023/1545.
- **Perturbateurs endocriniens potentiels** : liste des 28 substances que la Commission européenne fait évaluer
  (page « Endocrine disruptors » de la DG GROW, secteur des cosmétiques).

## Limites connues

- Le système dit ce que contient la **liste déclarée**. Il ne dit jamais qu'un produit est « sans danger » : un
  allergène sous le seuil de déclaration peut être caché dans « PARFUM ».
- Les « perturbateurs endocriniens potentiels » sont des substances **en cours d'évaluation**, pas des perturbateurs
  avérés.
- La copie de CosIng date de 2016 : quelques ingrédients récents ne sont pas reconnus.
- Le classifieur reconnaît des listes qui ressemblent à celles des produits certifiés ; il ne remplace pas une
  certification.
