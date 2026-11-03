"""Brique 7 — un classifieur qui reconnaît les listes INCI qui ressemblent à celles des produits certifiés
bio ou naturels (Ecocert, COSMOS, Cosmébio, Natrue…).

Pourquoi cette cible ? Une certification est attribuée par un organisme extérieur, en regardant l'origine
et le pourcentage des ingrédients : la liste INCI ne suffit pas à la deviner à coup sûr. C'est donc un vrai
problème d'apprentissage, et pas une règle que nous aurions écrite nous-mêmes.

Le modèle :
  1. chaque produit devient une ligne de 0 et de 1 : 1 si l'ingrédient est dans sa liste, 0 sinon
     (CountVectorizer, binary=True) ; on ne garde que les ingrédients présents dans au moins 5 produits ;
  2. une régression logistique apprend un poids par ingrédient : positif s'il pousse vers « certifié »,
     négatif s'il pousse vers « non certifié ». class_weight="balanced" compense le fait que les
     produits certifiés sont beaucoup moins nombreux.
"""
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

# Familles d'ingrédients synthétiques courants : la référence simple dit « non certifié » si on en trouve une.
MARQUEURS_SYNTHETIQUES = ["PEG-", "METHICONE", "SILOXANE", "PARABEN", "PARAFFINUM LIQUIDUM", "PETROLATUM", "EDTA"]


def separer_ingredients(texte):
    """Les ingrédients d'un produit sont stockés en une chaîne « AQUA|GLYCERIN|… »."""
    return texte.split("|")


def creer_modele():
    vectoriseur = CountVectorizer(tokenizer=separer_ingredients, lowercase=False, binary=True,
                                  min_df=5, token_pattern=None)
    regression = LogisticRegression(max_iter=2000, class_weight="balanced")
    return make_pipeline(vectoriseur, regression)


def reference_simple(texte_ingredients):
    """Référence sans apprentissage : 1 (« certifié ») si aucun marqueur synthétique n'apparaît, sinon 0."""
    for ingredient in separer_ingredients(texte_ingredients):
        for marqueur in MARQUEURS_SYNTHETIQUES:
            if marqueur in ingredient:
                return 0
    return 1


def ingredients_les_plus_influents(modele, combien=10):
    """Les ingrédients dont le poids est le plus fort, dans un sens et dans l'autre (pour la soutenance)."""
    vectoriseur, regression = modele.steps[0][1], modele.steps[1][1]
    noms = vectoriseur.get_feature_names_out()
    poids = regression.coef_[0]
    ordre = poids.argsort()
    vers_non_certifie = [(noms[i], round(float(poids[i]), 2)) for i in ordre[:combien]]
    vers_certifie = [(noms[i], round(float(poids[i]), 2)) for i in ordre[::-1][:combien]]
    return vers_certifie, vers_non_certifie
