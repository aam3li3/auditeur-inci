"""Affiche une trace JSONL de façon lisible, pour expliquer ce qui s'est passé (brique 9).

Usage : python -m evaluation.voir_trace evaluation/resultats/traces/systeme_l1_c01.jsonl
"""
import json
import sys


def afficher(chemin):
    with open(chemin, encoding="utf-8") as f:
        for ligne in f:
            e = json.loads(ligne)
            if e["type"] == "question":
                print(f"=== QUESTION ({e['mode']}, graine {e['graine']})\n{e['texte']}\n")
            elif e["type"] == "modele":
                print(f"--- MODÈLE, tour {e['tour']}")
                if e.get("contenu"):
                    print(e["contenu"].strip())
                for appel in e.get("appels") or []:
                    print(f"    → appel {appel['function']['name']}({appel['function'].get('arguments')})")
            elif e["type"] == "outil":
                print(f"    ← {e['nom']} [{e['statut'].upper()}] {e['resultat'][:600]}")
            elif e["type"] == "garde":
                action = "VERDICT REMPLACÉ" if e["bloque"] else "verdict accepté"
                print(f"    ■ GARDE : modèle = {e['verdict_modele']}, final = {e['verdict_final']} → {action}"
                      + (f" ({' ; '.join(e['raisons'])})" if e["raisons"] else ""))
            elif e["type"] == "fin":
                print(f"\n=== FIN : réponse = {e['reponse']}, verdict = {e['verdict']}, {e['tokens']} tokens"
                      + (f" ({e['raison']})" if e.get("raison") else ""))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    afficher(sys.argv[1])
