"""Brique 9 — le système (Qwen + outils + garde) face à Qwen seul, sur les tâches à réponse connue.

Chaque tâche est posée dans les deux modes, à chaque lancement (graine = numéro du lancement).
Tout est écrit au fil de l'eau : evaluation/resultats/lancements.jsonl (une ligne par exécution),
une trace par exécution dans evaluation/resultats/traces/, et le résumé dans resume_benchmark.md.

Usage : python -m evaluation.benchmark --lancements 3
        python -m evaluation.benchmark --lancements 1 --limite 1     (essai rapide : 1 tâche par type)
"""
import argparse
import json
import time

import pandas as pd
import requests

from src.agent import Trace, executer
from src.config import DOSSIER_RESULTATS, FICHIER_PROPRE, FICHIER_TACHES
from src.demarrage import charger_outils
from src.garde import preparer_allergies, verdict_minimum
from src.llm import ClientLLM

MODES = ["modele_seul", "systeme"]


def charger_taches():
    with open(FICHIER_TACHES, encoding="utf-8") as f:
        return [json.loads(ligne) for ligne in f if ligne.strip()]


def executer_tache(tache, mode, lancement, client, outils):
    trace = Trace(DOSSIER_RESULTATS / "traces" / f"{mode}_l{lancement}_{tache['id']}.jsonl")
    debut = time.monotonic()
    if mode == "systeme":
        verdict_autorise = None
        if tache["type"] == "compatibilite":  # la garde ne concerne que les questions de compatibilité
            allergies = preparer_allergies(tache["allergies"], outils.lecteur)
            verdict_autorise = verdict_minimum(outils.lecteur.lire(tache["texte_inci"]), allergies, outils.allergenes)
        resultat = executer(tache["question"], client, outils=outils, verdict_autorise=verdict_autorise,
                            graine=lancement, trace=trace)
    else:
        resultat = executer(tache["question"], client, graine=lancement, trace=trace)

    obtenu = resultat["verdict"] if tache["type"] == "compatibilite" else resultat["reponse"]
    statuts = [e["statut"] for e in trace.evenements if e["type"] == "outil"]
    gardes = [e for e in trace.evenements if e["type"] == "garde"]
    return {
        "lancement": lancement, "mode": mode, "id": tache["id"], "type": tache["type"],
        "attendu": tache["attendu"], "obtenu": obtenu, "correct": obtenu == tache["attendu"],
        # Erreur dangereuse : dire COMPATIBLE alors que la bonne réponse est INCOMPATIBLE ou INCERTAIN
        "dangereux": tache["type"] == "compatibilite" and obtenu == "COMPATIBLE" and tache["attendu"] != "COMPATIBLE",
        "tokens": resultat["tokens"], "tours": resultat["tours"], "duree_s": round(time.monotonic() - debut, 1),
        "appels_outils": len(statuts), "erreurs_outils": sum(s != "ok" for s in statuts),
        "bloque_par_la_garde": any(g["bloque"] for g in gardes),
        "trace": str(trace.chemin.relative_to(DOSSIER_RESULTATS.parent.parent)),
    }


def resumer(lignes):
    """Exactitude de chaque lancement, puis moyenne et dispersion entre lancements, par mode et type de tâche."""
    df = pd.DataFrame(lignes)
    par_lancement = df.groupby(["mode", "type", "lancement"])["correct"].mean().reset_index()
    return (par_lancement.groupby(["mode", "type"])["correct"]
            .agg(moyenne="mean", ecart_type="std", minimum="min", maximum="max", lancements="count")
            .reset_index())


def ecrire_resume(lignes, client):
    df = pd.DataFrame(lignes)
    out = ["# Brique 9 — Système contre modèle seul", "",
           f"Modèle : `{client.modele}` via `{client.url}`, température {client.temperature}. "
           f"{df['lancement'].nunique()} lancement(s), {df['id'].nunique()} tâches, {len(df)} exécutions.", "",
           "## Exactitude (moyenne ± écart-type entre lancements)", "",
           "| Mode | Type de tâche | Moyenne | Écart-type | Min | Max | Lancements |", "|---|---|---|---|---|---|---|"]
    for r in resumer(lignes).itertuples():
        out.append(f"| {r.mode} | {r.type} | {r.moyenne:.1%} | {r.ecart_type:.1%} | {r.minimum:.1%} | "
                   f"{r.maximum:.1%} | {r.lancements} |")
    total = df.groupby(["mode", "lancement"])["correct"].mean().groupby("mode").agg(["mean", "std"])
    out += ["", "| Mode | Toutes tâches : moyenne | Écart-type |", "|---|---|---|"]
    out += [f"| {mode} | {r['mean']:.1%} | {r['std']:.1%} |" for mode, r in total.iterrows()]
    couts = df.groupby("mode").agg(tokens=("tokens", "mean"), duree_s=("duree_s", "mean"), tours=("tours", "mean"),
                                   erreurs=("erreurs_outils", "sum"), garde=("bloque_par_la_garde", "sum"),
                                   dangereux=("dangereux", "sum"), hors_format=("obtenu", lambda s: s.isna().sum()))
    out += ["", "## Sécurité, coût et comportement", "",
            "| Mode | Verdicts dangereux (COMPATIBLE à tort) | Verdicts corrigés par la garde | Tokens moyens "
            "| Durée moyenne (s) | Tours moyens | Erreurs d'outil | Réponses hors format |",
            "|---|---|---|---|---|---|---|---|"]
    for mode, r in couts.iterrows():
        out.append(f"| {mode} | {r.dangereux:.0f} | {r.garde:.0f} | {r.tokens:.0f} | {r.duree_s:.1f} | "
                   f"{r.tours:.1f} | {r.erreurs:.0f} | {r.hors_format:.0f} |")
    echecs = df[(df["mode"] == "systeme") & (~df["correct"])]
    out += ["", "## Échecs du système (à analyser à partir de leur trace)", "",
            "| Lancement | Tâche | Attendu | Obtenu | Trace |", "|---|---|---|---|---|"]
    out += [f"| {r.lancement} | {r.id} | {r.attendu} | {r.obtenu} | `{r.trace}` |" for r in echecs.itertuples()]
    out += ["", "Lire une trace : `python -m evaluation.voir_trace <fichier>`.", ""]
    (DOSSIER_RESULTATS / "resume_benchmark.md").write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--lancements", type=int, default=3)
    parser.add_argument("--limite", type=int, default=None, help="ne garder que les N premières tâches de chaque type")
    args = parser.parse_args()

    taches = charger_taches()
    if args.limite:
        types = ["allergenes", "perturbateurs", "compatibilite"]
        taches = [t for typ in types for t in [x for x in taches if x["type"] == typ][:args.limite]]
    client, outils = ClientLLM(), charger_outils()
    total = args.lancements * len(MODES) * len(taches)
    print(f"{len(taches)} tâches × {len(MODES)} modes × {args.lancements} lancements = {total} exécutions")

    lignes = []
    journal = DOSSIER_RESULTATS / "lancements.jsonl"
    journal.write_text("", encoding="utf-8")
    try:
        for lancement in range(1, args.lancements + 1):
            for mode in MODES:
                for tache in taches:
                    ligne = executer_tache(tache, mode, lancement, client, outils)
                    lignes.append(ligne)
                    with journal.open("a", encoding="utf-8") as f:
                        f.write(json.dumps(ligne, ensure_ascii=False) + "\n")
                    print(f"[{len(lignes)}/{total}] l{lancement} {mode:11} {tache['id']}  attendu {ligne['attendu']:12} "
                          f"obtenu {str(ligne['obtenu']):12} {'✓' if ligne['correct'] else '✗'}  {ligne['duree_s']} s")
    except requests.ConnectionError:
        raise SystemExit(f"Serveur du modèle injoignable à {client.url} : lancez llama-server (voir README).")
    except KeyboardInterrupt:
        print("\nInterrompu : résumé des exécutions déjà faites.")
    if lignes:
        ecrire_resume(lignes, client)


if __name__ == "__main__":
    main()
