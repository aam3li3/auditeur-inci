# Brique 9 — Système contre modèle seul

Modèle : `qwen3.5:4b-q4_K_M` via `http://localhost:11434/v1`, température 0.7. 3 lancement(s), 12 tâches, 72 exécutions.

## Exactitude (moyenne ± écart-type entre lancements)

| Mode | Type de tâche | Moyenne | Écart-type | Min | Max | Lancements |
|---|---|---|---|---|---|---|
| modele_seul | allergenes | 41.7% | 38.2% | 0.0% | 75.0% | 3 |
| modele_seul | compatibilite | 66.7% | 23.1% | 40.0% | 80.0% | 3 |
| modele_seul | perturbateurs | 44.4% | 19.2% | 33.3% | 66.7% | 3 |
| systeme | allergenes | 91.7% | 14.4% | 75.0% | 100.0% | 3 |
| systeme | compatibilite | 100.0% | 0.0% | 100.0% | 100.0% | 3 |
| systeme | perturbateurs | 100.0% | 0.0% | 100.0% | 100.0% | 3 |

| Mode | Toutes tâches : moyenne | Écart-type |
|---|---|---|
| modele_seul | 52.8% | 4.8% |
| systeme | 97.2% | 4.8% |

## Sécurité, coût et comportement

| Mode | Verdicts dangereux (COMPATIBLE à tort) | Verdicts corrigés par la garde | Tokens moyens | Durée moyenne (s) | Tours moyens | Erreurs d'outil | Réponses hors format |
|---|---|---|---|---|---|---|---|
| modele_seul | 4 | 0 | 395 | 5.8 | 1.0 | 0 | 0 |
| systeme | 0 | 0 | 2682 | 18.1 | 2.1 | 0 | 1 |

## Échecs du système (à analyser à partir de leur trace)

| Lancement | Tâche | Attendu | Obtenu | Trace |
|---|---|---|---|---|
| 1 | a01 | 0 | None | `evaluation/resultats/traces/systeme_l1_a01.jsonl` |

Lire une trace : `python -m evaluation.voir_trace <fichier>`.
