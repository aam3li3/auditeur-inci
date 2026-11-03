"""Étape 0 — extrait de l'export Open Beauty Facts (beauty.parquet) les colonnes utiles au projet.

Source : base Open Beauty Facts, licence Open Database License (ODbL), export Parquet publié sur
Hugging Face (dépôt openfoodfacts/product-database, fichier beauty.parquet), version téléchargée
le 01/11/2026 (empreinte sha256 notée ci-dessous).

Ce script :
  - ne garde que 8 colonnes (code, nom, marque, liste INCI, labels, pays, catégories, langue) ;
  - laisse de côté toutes les colonnes qui contiennent des pseudonymes de contributeurs (creator,
    editors, last_editor, photographers…) : aucune donnée personnelle n'entre dans le dépôt (R1) ;
  - ne garde que les produits qui ont une liste d'ingrédients.
Il ne corrige rien : le vrai nettoyage est fait par src/nettoyage.py, avec son journal.

Usage : python -m src.preparer_donnees chemin/vers/beauty.parquet
        python -m src.preparer_donnees --telecharger        (télécharge la version du jour, ~65 Mo)
"""
import argparse
import hashlib

import pandas as pd
import requests

from src.config import FICHIER_BRUT, RACINE

URL = "https://huggingface.co/datasets/openfoodfacts/product-database/resolve/main/beauty.parquet"
EMPREINTE_VERSION_UTILISEE = "62f7eaee35dec4468de1575a037abe9a1e2c44fa8c11536fcbdd2587ad6123d3"
COLONNES = ["code", "brands", "product_name", "ingredients_text", "labels_tags", "countries_tags",
            "categories_tags", "lang"]


def texte_principal(valeurs, langue):
    """Dans le fichier, un texte est une liste de versions : [{"lang": "main", "text": …}, {"lang": "fr", …}].
    On prend la version principale (« main »), sinon celle de la langue du produit, sinon la première."""
    if valeurs is None:
        return ""
    for preference in ("main", langue):
        for version in valeurs:
            if version["lang"] == preference and version["text"]:
                return version["text"]
    for version in valeurs:
        if version["text"]:
            return version["text"]
    return ""


def joindre(valeurs):
    """Une liste de labels ['en:organic', 'fr:ecocert'] devient le texte « en:organic,fr:ecocert »."""
    return "" if valeurs is None else ",".join(valeurs)


def preparer(chemin_parquet):
    brut = pd.read_parquet(chemin_parquet, columns=COLONNES)
    extrait = pd.DataFrame({
        "code": brut["code"],
        "nom": [texte_principal(v, l) for v, l in zip(brut["product_name"], brut["lang"])],
        "marque": brut["brands"].fillna(""),
        "texte_inci": [texte_principal(v, l) for v, l in zip(brut["ingredients_text"], brut["lang"])],
        "labels": brut["labels_tags"].apply(joindre),
        "pays": brut["countries_tags"].apply(joindre),
        "categories": brut["categories_tags"].apply(joindre),
        "langue": brut["lang"].fillna(""),
    })
    avec_liste = extrait[extrait["texte_inci"].str.strip() != ""]
    print(f"{len(brut)} produits dans l'export, {len(avec_liste)} avec une liste d'ingrédients")
    FICHIER_BRUT.parent.mkdir(parents=True, exist_ok=True)
    avec_liste.to_csv(FICHIER_BRUT, index=False)
    print(f"Écrit : {FICHIER_BRUT.relative_to(RACINE)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("chemin", nargs="?", help="chemin du fichier beauty.parquet déjà téléchargé")
    parser.add_argument("--telecharger", action="store_true")
    args = parser.parse_args()
    if args.telecharger:
        chemin = RACINE / "data" / "brut" / "beauty.parquet"
        chemin.write_bytes(requests.get(URL, timeout=600).content)
    elif args.chemin:
        chemin = args.chemin
    else:
        raise SystemExit(__doc__)
    with open(chemin, "rb") as f:
        empreinte = hashlib.sha256(f.read()).hexdigest()
    if empreinte != EMPREINTE_VERSION_UTILISEE:
        print("Attention : ce n'est pas la version utilisée pour les résultats du dépôt (la base change chaque jour).")
    preparer(chemin)


if __name__ == "__main__":
    main()
