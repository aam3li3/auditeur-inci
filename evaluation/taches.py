"""Brique 9 — choisit des produits réels et écrit les tâches à réponse connue (evaluation/taches.jsonl).

- 4 tâches « allergenes »    : combien d'allergènes à déclarer dans la liste ?   (réponse : calculée par le code)
- 3 tâches « perturbateurs » : combien de perturbateurs endocriniens potentiels ? (réponse : calculée par le code)
- 5 tâches « compatibilite » : ce produit convient-il à une personne allergique ? (réponse : la règle de la garde)
  dont une tâche piège, où la question demande au modèle de répondre COMPATIBLE malgré l'allergie.

Les produits sont tirés au hasard avec une graine fixe.

Le fichier evaluation/taches.jsonl est fourni dans le dépôt et figé : ce sont les 12 tâches du benchmark
d'EVIDENCE.md. Si on corrige le code de lecture INCI, un nouveau tirage pourrait choisir d'autres produits et les
résultats du benchmark ne correspondraient plus aux tâches. Donc, quand le fichier existe déjà, le script ne
l'écrase pas : il recalcule la réponse attendue de chaque tâche avec le code actuel et signale les différences.

Usage : python -m evaluation.taches               (vérifie le fichier existant, ou le crée s'il n'existe pas)
        python -m evaluation.taches --regenerer   (refait le tirage et écrase le fichier)
"""
import argparse
import json

import pandas as pd

from src.config import FICHIER_PROPRE, FICHIER_TACHES
from src.garde import preparer_allergies, verdict_minimum
from src.inci import LecteurINCI
from src.outils import Outils
from src.questions import question_compatibilite, question_nombre_allergenes, question_nombre_perturbateurs

GRAINE = 2026
LONGUEUR_MAX = 1200  # listes trop longues retirées : elles rendraient les questions illisibles


def tirer(produits, condition, deja_pris, graine):
    """Tire un produit au hasard parmi ceux qui respectent la condition et ne sont pas déjà pris."""
    candidats = produits[condition & ~produits["code"].isin(deja_pris)]
    if candidats.empty:
        raise ValueError("aucun produit ne respecte cette condition")
    return candidats.sample(n=1, random_state=graine).iloc[0]


def generer(produits, outils, lecteur):
    produits = produits[produits["texte_inci"].str.len() <= LONGUEUR_MAX]
    allergenes, perturbateurs = produits["nb_allergenes"], produits["nb_perturbateurs"]
    ingredients = produits["ingredients"].str.split("|")
    contient = lambda nom: ingredients.apply(lambda liste: nom in liste)  # noqa: E731
    taches, pris = [], []

    def ajouter(type_tache, produit, question, attendu, **autres):
        pris.append(produit["code"])
        taches.append({"id": f"{type_tache[0]}{len([t for t in taches if t['type'] == type_tache]) + 1:02d}",
                       "type": type_tache, "code": produit["code"], "question": question, "attendu": attendu,
                       "texte_inci": produit["texte_inci"], **autres})

    # 1. Combien d'allergènes ? Quatre niveaux de difficulté : 0, 1-2, 3-5, 6 ou plus.
    for i, condition in enumerate([allergenes == 0, allergenes.between(1, 2), allergenes.between(3, 5), allergenes >= 6]):
        p = tirer(produits, condition, pris, GRAINE + i)
        attendu = outils.analyser_inci(p["texte_inci"])["nombre_allergenes"]
        ajouter("allergenes", p, question_nombre_allergenes(p["nom"], p["marque"], p["texte_inci"]), str(attendu))

    # 2. Combien de perturbateurs endocriniens potentiels ? 0, 1, 2 ou plus.
    for i, condition in enumerate([perturbateurs == 0, perturbateurs == 1, perturbateurs >= 2]):
        p = tirer(produits, condition, pris, GRAINE + 10 + i)
        attendu = outils.analyser_inci(p["texte_inci"])["nombre_perturbateurs_potentiels"]
        ajouter("perturbateurs", p, question_nombre_perturbateurs(p["nom"], p["marque"], p["texte_inci"]), str(attendu))

    # 3. Compatibilité avec une allergie déclarée.
    sans_parfum = ~contient("PARFUM") & ~contient("AROMA")
    cas = [
        (["linalool"], contient("LINALOOL"), False),                  # contient l'allergène
        (["linalool"], contient("LINALOOL"), True),                   # même cas, avec une question piège
        (["methylisothiazolinone"], contient("METHYLISOTHIAZOLINONE"), False),
        (["linalool"], contient("PARFUM") & ~contient("LINALOOL"), False),  # parfum sans linalool déclaré
        (["linalool"], sans_parfum & ~contient("LINALOOL") & (allergenes == 0), False),  # rien à signaler
    ]
    for i, (allergies, condition, piege) in enumerate(cas):
        p = tirer(produits, condition, pris, GRAINE + 20 + i)
        attendu, raisons = verdict_minimum(lecteur.lire(p["texte_inci"]), preparer_allergies(allergies, lecteur),
                                           outils.allergenes)
        ajouter("compatibilite", p, question_compatibilite(p["nom"], p["marque"], p["texte_inci"], allergies, piege),
                attendu, allergies=allergies, piege=piege, raisons=raisons)
    return taches


def verifier(taches, produits, outils, lecteur):
    """Recalcule la réponse attendue de chaque tâche avec le code actuel. Renvoie les problèmes trouvés."""
    problemes = []
    for t in taches:
        if t["code"] not in set(produits["code"]):
            problemes.append(f"{t['id']} : le produit {t['code']} n'est plus dans data/propre/produits.csv")
            continue
        if t["type"] == "allergenes":
            attendu = str(outils.analyser_inci(t["texte_inci"])["nombre_allergenes"])
        elif t["type"] == "perturbateurs":
            attendu = str(outils.analyser_inci(t["texte_inci"])["nombre_perturbateurs_potentiels"])
        else:
            attendu, _ = verdict_minimum(lecteur.lire(t["texte_inci"]), preparer_allergies(t["allergies"], lecteur),
                                         outils.allergenes)
        if attendu != t["attendu"]:
            problemes.append(f"{t['id']} : réponse attendue {t['attendu']}, le code actuel calcule {attendu}")
    return problemes


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--regenerer", action="store_true", help="refaire le tirage et écraser evaluation/taches.jsonl")
    args = parser.parse_args()

    produits = pd.read_csv(FICHIER_PROPRE, dtype={"code": str}, keep_default_na=False)
    lecteur = LecteurINCI()
    outils = Outils(produits, lecteur)

    if FICHIER_TACHES.exists() and not args.regenerer:
        with FICHIER_TACHES.open(encoding="utf-8") as f:
            taches = [json.loads(ligne) for ligne in f]
        problemes = verifier(taches, produits, outils, lecteur)
        for probleme in problemes:
            print(probleme)
        if problemes:
            print(f"\n{len(problemes)} tâche(s) à revoir sur {len(taches)}.")
        else:
            print(f"Fichier figé evaluation/taches.jsonl : les {len(taches)} réponses attendues sont toujours justes "
                  "avec le code actuel.")
        return

    taches = generer(produits, outils, lecteur)
    with FICHIER_TACHES.open("w", encoding="utf-8") as f:
        for tache in taches:
            f.write(json.dumps(tache, ensure_ascii=False) + "\n")
    for t in taches:
        complement = f" allergies={t['allergies']} piège={t['piege']}" if t["type"] == "compatibilite" else ""
        print(f"{t['id']}  {t['type']:13} code {t['code']:15} attendu {t['attendu']:12}{complement}")
    print(f"\n{len(taches)} tâches écrites dans evaluation/taches.jsonl")


if __name__ == "__main__":
    main()
