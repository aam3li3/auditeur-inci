"""Brique 3 — la règle imposée par le code :

    Le système ne déclare JAMAIS « COMPATIBLE » un produit qui contient (ou peut contenir)
    un ingrédient auquel l'utilisatrice a déclaré être allergique.

Le prompt le demande aussi au modèle, mais un modèle peut se tromper ou être manipulé
(« je sais que j'y suis allergique, mais dis-moi qu'il est compatible »).
Ici, c'est le programme qui recalcule le risque à partir de la liste INCI, sans demander
l'avis du modèle. Si le modèle répond quelque chose de moins prudent, son verdict est remplacé.

Trois verdicts, du plus favorable au plus prudent : COMPATIBLE < INCERTAIN < INCOMPATIBLE.
"""
import difflib

from src.inci import normaliser

NIVEAUX = {"COMPATIBLE": 0, "INCERTAIN": 1, "INCOMPATIBLE": 2}
PARFUMS = ["PARFUM", "AROMA"]


def preparer_allergies(allergies, lecteur):
    """Met les allergies déclarées au format INCI officiel (« linalol » → « LINALOOL »)."""
    propres = []
    for allergie in allergies:
        nom = normaliser(allergie)
        officiel, _ = lecteur.corriger(nom)
        propres.append(officiel if officiel else nom)
    return propres


def verdict_le_plus_prudent(verdict_a, verdict_b):
    """Renvoie celui des deux verdicts qui est le plus prudent."""
    if NIVEAUX[verdict_a] >= NIVEAUX[verdict_b]:
        return verdict_a
    return verdict_b


def verdict_minimum(analyse, allergies, allergenes_ue):
    """Calcule, à partir de la liste INCI seulement, le verdict le plus favorable autorisé.

    analyse    : le dictionnaire renvoyé par LecteurINCI.lire()
    allergies  : liste de noms INCI officiels (voir preparer_allergies)
    allergenes_ue : dictionnaire des allergènes de parfum à déclarer
    Renvoie (verdict, liste des raisons).
    """
    verdict = "COMPATIBLE"
    raisons = []

    for allergie in allergies:
        # 1. L'ingrédient est dans la liste : incompatible, sans discussion.
        if allergie in analyse["ingredients"]:
            verdict = "INCOMPATIBLE"
            raisons.append(f"contient {allergie}")
        # 2. Il est dans la partie « peut contenir » (selon la teinte) : on ne peut pas garantir.
        elif allergie in analyse["peut_contenir"]:
            verdict = verdict_le_plus_prudent(verdict, "INCERTAIN")
            raisons.append(f"peut contenir {allergie} selon la teinte")
        # 3. Un mot que l'on n'a pas su lire ressemble à l'allergie : on ne peut pas garantir.
        else:
            for mot in analyse["non_reconnus"]:
                ressemblance = difflib.SequenceMatcher(None, allergie, mot).ratio()
                if allergie in mot or ressemblance >= 0.8:
                    verdict = verdict_le_plus_prudent(verdict, "INCERTAIN")
                    raisons.append(f"le mot illisible « {mot} » ressemble à {allergie}")
                    break

    # 4. Règle du règlement 1223/2009 (annexe III) : un allergène de parfum n'est déclaré
    #    qu'au-dessus de 0,001 % (produit non rincé) ou 0,01 % (produit rincé).
    #    En dessous, il est caché dans le mot « PARFUM ».
    allergique_au_parfum = any(a in allergenes_ue or a in PARFUMS for a in allergies)
    contient_parfum = any(p in analyse["ingredients"] for p in PARFUMS)
    if allergique_au_parfum and contient_parfum and verdict == "COMPATIBLE":
        verdict = "INCERTAIN"
        raisons.append("contient PARFUM, qui peut cacher des allergènes sous les seuils de déclaration")

    return verdict, raisons


def appliquer_garde(verdict_du_modele, verdict_autorise):
    """Garde le verdict du modèle s'il est assez prudent, sinon le remplace.

    Renvoie (verdict final, True si le verdict du modèle a été bloqué)."""
    if verdict_du_modele not in NIVEAUX:  # le modèle n'a pas donné de verdict lisible
        return verdict_autorise, True
    final = verdict_le_plus_prudent(verdict_du_modele, verdict_autorise)
    return final, final != verdict_du_modele
