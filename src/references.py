"""Chargement des listes de référence (dossier data/reference/).

- inci_cosing.csv              : les 24 100 noms INCI officiels de la base européenne CosIng
- allergenes_ue.csv            : les allergènes de parfum à déclarer (règlement 1223/2009, annexe III,
                                 complété par le règlement (UE) 2023/1545)
- perturbateurs_potentiels.csv : les 28 substances que la Commission européenne fait évaluer
                                 pour un possible effet perturbateur endocrinien
- synonymes.csv                : les autres façons d'écrire un même ingrédient (WATER → AQUA…)
"""
import csv

from src.config import DOSSIER_REFERENCE


def lire_csv(nom_fichier, separateur=";"):
    """Lit un fichier CSV du dossier de référence et renvoie une liste de dictionnaires."""
    chemin = DOSSIER_REFERENCE / nom_fichier
    with open(chemin, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter=separateur))


def charger_allergenes():
    """Dictionnaire {nom INCI : ligne du fichier} des allergènes à déclarer."""
    allergenes = {}
    for ligne in lire_csv("allergenes_ue.csv"):
        allergenes[ligne["nom_inci"]] = ligne
    return allergenes


def charger_perturbateurs():
    """Dictionnaire {nom INCI : ligne du fichier} des perturbateurs endocriniens potentiels."""
    perturbateurs = {}
    for ligne in lire_csv("perturbateurs_potentiels.csv"):
        perturbateurs[ligne["nom_inci"]] = ligne
    return perturbateurs


def charger_synonymes():
    """Dictionnaire {variante : nom INCI officiel}, par exemple {"WATER": "AQUA"}."""
    synonymes = {}
    for ligne in lire_csv("synonymes.csv"):
        synonymes[ligne["variante"]] = ligne["nom_inci"]
    return synonymes


def charger_noms_inci():
    """Ensemble de tous les noms INCI connus : CosIng + nos deux listes (certains allergènes
    ajoutés en 2023 sont plus récents que notre copie de CosIng, qui date de 2016)."""
    noms = set()
    for ligne in lire_csv("inci_cosing.csv", separateur=","):
        noms.add(ligne["nom_inci"])
    noms.update(charger_allergenes().keys())
    noms.update(charger_perturbateurs().keys())
    return noms
