"""Brique 6 — nettoyage des produits Open Beauty Facts, avec un journal chiffré de chaque décision.

Entrée  : data/brut/produits_bruts.csv.gz (produit par src/preparer_donnees.py)
Sorties : data/propre/produits.csv et data/journal_nettoyage.md

Usage : python -m src.nettoyage       (environ 1 min 30 : chaque liste INCI est lue et corrigée)
"""
import re
from collections import Counter

import pandas as pd

from src.config import FICHIER_BRUT, FICHIER_JOURNAL, FICHIER_PROPRE
from src.inci import LecteurINCI
from src.references import charger_allergenes, charger_perturbateurs, lire_csv

SEUIL_RECONNAISSANCE = 0.8  # une liste dont moins de 80 % des morceaux sont reconnus est jugée illisible

# Mentions « bio » ou « naturel » qui ne désignent pas un organisme certificateur de cosmétiques
AMBIGU = re.compile(r"(^|-)(organic|bio|natural|naturel|naturelle|natur|naturkosmetik)(-|$)")


def lire_certification(labels, motifs):
    """À partir des labels d'un produit (« en:vegan,fr:ecocert-cosmos-organic »), renvoie
    (nom de la certification ou "", True si une mention « bio/naturel » ambiguë est présente)."""
    ambigu = False
    for tag in labels.split(","):
        nom = tag.split(":", 1)[-1].strip().lower()  # « fr:ecocert » → « ecocert »
        if not nom or nom == "non-organic":
            continue
        for motif, certification in motifs:
            if motif in nom:
                return certification, False
        if AMBIGU.search(nom):
            ambigu = True
    return "", ambigu


def nettoyer(brut, lecteur, allergenes, perturbateurs, motifs):
    """Renvoie (produits propres, journal, statistiques pour le journal)."""
    journal = []
    df = brut.copy()

    def noter(etape, avant, decision):
        journal.append({"etape": etape, "avant": avant, "apres": len(df), "decision": decision})

    # 1. Un même code-barres en double : on garde la première fiche.
    n = len(df)
    df = df.drop_duplicates("code")
    noter("Codes-barres en double", n, "une seule fiche gardée par code-barres")

    # 2. Lecture de chaque liste INCI : découpage, noms officiels, fautes corrigées.
    lectures = [lecteur.lire(texte) for texte in df["texte_inci"]]
    comptes = Counter()
    corrections = Counter()
    non_reconnus = Counter()
    for lecture in lectures:
        comptes.update(lecture["comment"])
        corrections.update(lecture["corrections"])
        non_reconnus.update(lecture["non_reconnus"])
    df["ingredients"] = ["|".join(l["ingredients"]) for l in lectures]
    df["peut_contenir"] = ["|".join(l["peut_contenir"]) for l in lectures]
    df["part_reconnue"] = [l["part_reconnue"] for l in lectures]
    df["nb_ingredients"] = [len(l["ingredients"]) for l in lectures]
    noter("Lecture des listes INCI", len(df),
          f"{sum(comptes.values())} morceaux lus : {comptes['exact']} noms officiels, {comptes['synonyme']} synonymes "
          f"remplacés (WATER → AQUA…), {comptes['double_nom']} doubles noms (« PARFUM/FRAGRANCE »), "
          f"{comptes['corrige']} fautes corrigées, {comptes['inconnu']} non reconnus")

    # 3. Listes illisibles : écrites dans une autre langue, coupées par l'OCR, ou pas des listes INCI.
    n = len(df)
    df = df[(df["part_reconnue"] >= SEUIL_RECONNAISSANCE) & (df["nb_ingredients"] > 0)]
    noter("Listes illisibles", n, f"moins de {SEUIL_RECONNAISSANCE:.0%} des morceaux reconnus : liste retirée")

    # 4. Même marque et même formule : c'est le même produit (autre contenance, autre code-barres).
    n = len(df)
    df["marque"] = df["marque"].fillna("").str.split(",").str[0].str.strip()
    cle_marque = df["marque"].str.lower()
    df = df[~pd.DataFrame({"m": cle_marque, "i": df["ingredients"]}).duplicated()]
    noter("Même marque, même formule", n, "un seul produit gardé (souvent le même produit en plusieurs tailles)")

    # 5. Certification bio ou naturelle, à partir de labels écrits de dizaines de façons.
    resultats = [lire_certification(labels, motifs) for labels in df["labels"]]
    df["certification"] = [r[0] for r in resultats]
    ambigus = pd.Series([r[1] for r in resultats], index=df.index)
    sans_label = df["labels"].str.strip() == ""
    df["cible"] = ""
    df.loc[df["certification"] != "", "cible"] = "1"
    df.loc[(df["certification"] == "") & ~ambigus & ~sans_label, "cible"] = "0"
    noter("Certification", len(df),
          f"{(df['cible'] == '1').sum()} certifiés ; {(df['cible'] == '0').sum()} non certifiés (labels renseignés, "
          f"aucune certification) ; {(ambigus & (df['certification'] == '')).sum()} avec une simple mention "
          f"« bio » ou « naturel » et {sans_label.sum()} sans aucun label : exclus de l'apprentissage")

    # 6. Colonnes calculées, utiles aux outils et aux tâches du benchmark.
    def compter(texte, liste):
        return sum(1 for nom in texte.split("|") if nom in liste) if texte else 0
    tous = df["ingredients"] + "|" + df["peut_contenir"]
    df["nb_allergenes"] = [compter(t, allergenes) for t in tous]
    df["nb_perturbateurs"] = [compter(t, perturbateurs) for t in tous]
    df["contient_parfum"] = [("PARFUM" in t.split("|")) or ("AROMA" in t.split("|")) for t in df["ingredients"]]

    colonnes = ["code", "nom", "marque", "texte_inci", "ingredients", "peut_contenir", "nb_ingredients",
                "part_reconnue", "nb_allergenes", "nb_perturbateurs", "contient_parfum", "certification", "cible"]
    statistiques = {"corrections": corrections, "non_reconnus": non_reconnus,
                    "certifications": Counter(df.loc[df["certification"] != "", "certification"])}
    return df[colonnes].reset_index(drop=True), journal, statistiques


def ecrire_journal(journal, statistiques, total_export, propres):
    lignes = [
        "# Journal de nettoyage", "",
        "Produit par `python -m src.nettoyage`. Source : Open Beauty Facts (licence ODbL), export `beauty.parquet` "
        "du 01/11/2026, extrait par `python -m src.preparer_donnees`.", "",
        f"Export complet : **{total_export} produits**, dont **{journal[0]['avant']}** avec une liste d'ingrédients "
        f"(étape 0). Produits gardés à la fin : **{len(propres)}**.", "",
        "| # | Étape | Avant | Après | Retirés | Décision |", "|---|---|---|---|---|---|",
    ]
    for i, e in enumerate(journal, 1):
        lignes.append(f"| {i} | {e['etape']} | {e['avant']} | {e['apres']} | {e['avant'] - e['apres']} | {e['decision']} |")
    lignes += ["", "## Les 15 fautes corrigées le plus souvent", "", "| Écrit sur l'emballage | Nom officiel | Fois |",
               "|---|---|---|"]
    for (avant, apres), fois in statistiques["corrections"].most_common(15):
        lignes.append(f"| {avant} | {apres} | {fois} |")
    lignes += ["", "## Les 15 morceaux non reconnus le plus souvent (exemples de saleté)", "", "| Morceau | Fois |",
               "|---|---|"]
    for morceau, fois in statistiques["non_reconnus"].most_common(15):
        lignes.append(f"| {morceau[:90]} | {fois} |")
    lignes += ["", "## Certifications retrouvées dans les labels", "", "| Certification | Produits |", "|---|---|"]
    for certification, fois in statistiques["certifications"].most_common():
        lignes.append(f"| {certification} | {fois} |")
    lignes += [
        "", "## Règles que le fichier ne dit pas, et d'où elles viennent", "",
        "1. **Un allergène de parfum n'est déclaré qu'au-dessus d'un seuil** : 0,001 % dans un produit non rincé, "
        "0,01 % dans un produit rincé. En dessous, il reste caché dans le mot « PARFUM ». Source : règlement (CE) "
        "n° 1223/2009, annexe III, liste complétée par le règlement (UE) 2023/1545 (de 24 à environ 80 substances ; "
        "obligatoire pour les produits mis sur le marché depuis le 31/07/2026, et pour tous les produits vendus "
        "à partir du 31/07/2028). Conséquence : un allergène absent de la liste ne prouve pas qu'il est absent du "
        "produit. La garde (brique 3) en tient compte.",
        "2. **« +/- » ou « may contain » annonce des colorants qui ne sont pas dans toutes les teintes.** Source : "
        "règlement (CE) n° 1223/2009, article 19, paragraphe 1, point g). Ces ingrédients sont rangés à part "
        "(colonne `peut_contenir`).",
        "3. **L'ordre de la liste a un sens** : les ingrédients sont classés par quantité décroissante, sauf ceux "
        "à moins de 1 %. Même source. L'ordre est donc conservé.",
        "", "## Décisions personnelles (à défendre en soutenance)", "",
        f"- Une liste dont moins de {SEUIL_RECONNAISSANCE:.0%} des morceaux sont reconnus est retirée : elle est "
        "écrite dans une autre langue, coupée par l'OCR, ou remplacée par un texte (« please refer to the package »).",
        "- Une faute n'est corrigée que si le nom corrigé est très proche (ressemblance ≥ 90 %) et garde exactement "
        "les mêmes chiffres : PEG-40 ne devient jamais PEG-60.",
        "- Seuls les organismes certificateurs de cosmétiques comptent (Ecocert, COSMOS, Cosmébio, Natrue, BDIH, ICEA, "
        "Nature & Progrès, Soil Association). Une simple mention « bio », « organic » ou « 100 % naturel » est "
        "ambiguë : ces produits sont exclus de l'apprentissage, ni positifs ni négatifs.",
        "- Un produit sans aucun label n'est pas forcément non certifié (le contributeur a pu ne pas saisir les "
        "labels) : il est exclu de l'apprentissage. Les « non certifiés » sont les produits dont les labels ont été "
        "saisis (vegan, sans paraben…) sans aucune certification.",
        "", "Aucune donnée personnelle : les colonnes qui contiennent des pseudonymes de contributeurs ne sont jamais "
        "extraites de l'export.", ""]
    FICHIER_JOURNAL.write_text("\n".join(lignes), encoding="utf-8")


def main():
    brut = pd.read_csv(FICHIER_BRUT, dtype={"code": str}, keep_default_na=False)
    motifs = [(ligne["motif"], ligne["certification"]) for ligne in lire_csv("certifications.csv")]
    propres, journal, statistiques = nettoyer(brut, LecteurINCI(), charger_allergenes(), charger_perturbateurs(), motifs)
    FICHIER_PROPRE.parent.mkdir(parents=True, exist_ok=True)
    propres.to_csv(FICHIER_PROPRE, index=False)
    ecrire_journal(journal, statistiques, 79138, propres)
    for e in journal:
        print(f"{e['etape']:28} {e['avant']:>6} → {e['apres']:>6}")
    print(f"\n{len(propres)} produits écrits dans data/propre/produits.csv — journal : data/journal_nettoyage.md")


if __name__ == "__main__":
    main()
