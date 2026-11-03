"""Brique 7 — entraîne le classifieur et le compare à deux références simples, sur des marques jamais vues.

Découpage : 75 % des MARQUES pour apprendre, 25 % des marques pour tester. On découpe par marque et non par
produit : sinon le modèle pourrait reconnaître la « recette » d'une marque déjà vue (souvent toute la gamme
est certifiée) au lieu d'apprendre ce qui caractérise un produit certifié.

Usage : python -m evaluation.evaluer_classifieur
"""
import joblib
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import GroupShuffleSplit

from src.classifieur import creer_modele, ingredients_les_plus_influents, reference_simple
from src.config import DOSSIER_RESULTATS, FICHIER_MODELE, FICHIER_PROPRE


def mesures(vrais, predits):
    """Les quatre mesures, pour la classe 1 (« certifié »)."""
    return {
        "exactitude": accuracy_score(vrais, predits),
        "precision": precision_score(vrais, predits, zero_division=0),
        "rappel": recall_score(vrais, predits, zero_division=0),
        "f1": f1_score(vrais, predits, zero_division=0),
    }


def tableau_confusion(vrais, predits):
    m = confusion_matrix(vrais, predits, labels=[0, 1])
    return ["| réel \\ prédit | non certifié | certifié |", "|---|---|---|",
            f"| non certifié | {m[0][0]} | {m[0][1]} |", f"| certifié | {m[1][0]} | {m[1][1]} |"]


def main():
    produits = pd.read_csv(FICHIER_PROPRE, dtype={"code": str, "cible": str}, keep_default_na=False)
    donnees = produits[produits["cible"] != ""].copy()  # on garde les produits dont on connaît la réponse
    donnees["cible"] = donnees["cible"].astype(int)

    # Le groupe d'un produit = sa marque (en minuscules). Un produit sans marque forme son propre groupe.
    groupes = donnees["marque"].str.lower().str.strip()
    groupes = groupes.where(groupes != "", "sans-marque-" + donnees["code"])
    decoupage = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=42)
    index_appr, index_test = next(decoupage.split(donnees, groups=groupes))
    appr, test = donnees.iloc[index_appr], donnees.iloc[index_test]

    modele = creer_modele()
    modele.fit(appr["ingredients"], appr["cible"])

    majoritaire = DummyClassifier(strategy="most_frequent").fit(appr["ingredients"], appr["cible"])
    predictions = {
        "Régression logistique (notre modèle)": modele.predict(test["ingredients"]),
        "Référence : aucun ingrédient synthétique courant → certifié": [reference_simple(t) for t in test["ingredients"]],
        "Référence : toujours la classe la plus fréquente": majoritaire.predict(test["ingredients"]),
    }

    lignes = [
        "# Brique 7 — Reconnaître une liste INCI de produit certifié bio ou naturel", "",
        "Produit par `python -m evaluation.evaluer_classifieur`.", "",
        f"- Produits dont la réponse est connue : **{len(donnees)}** "
        f"({int(donnees['cible'].sum())} certifiés, {int((donnees['cible'] == 0).sum())} non certifiés).",
        f"- Apprentissage : {len(appr)} produits de {appr['marque'].nunique()} marques. "
        f"Test : **{len(test)} produits de {test['marque'].nunique()} autres marques**, jamais vues pendant "
        f"l'apprentissage ({int(test['cible'].sum())} certifiés).",
        f"- Ingrédients utilisés comme variables (présents dans au moins 5 produits) : "
        f"{len(modele.steps[0][1].get_feature_names_out())}.", "",
        "| Modèle | Exactitude | Précision | Rappel | F1 |", "|---|---|---|---|---|",
    ]
    for nom, predits in predictions.items():
        m = mesures(test["cible"], predits)
        lignes.append(f"| {nom} | {m['exactitude']:.1%} | {m['precision']:.1%} | {m['rappel']:.1%} | {m['f1']:.2f} |")
    lignes += ["", "Précision : parmi les produits annoncés « certifiés », la part qui l'est vraiment. "
               "Rappel : parmi les produits vraiment certifiés, la part retrouvée. F1 : moyenne des deux.", "",
               "## Matrice de confusion de notre modèle", ""]
    lignes += tableau_confusion(test["cible"], predictions["Régression logistique (notre modèle)"])
    lignes += ["", "## Matrice de confusion de la référence « aucun ingrédient synthétique courant »", ""]
    lignes += tableau_confusion(test["cible"], predictions["Référence : aucun ingrédient synthétique courant → certifié"])

    vers_certifie, vers_non_certifie = ingredients_les_plus_influents(modele)
    lignes += ["", "## Ce que le modèle a appris (les poids les plus forts)", "",
               "| Pousse vers « certifié » | Poids | Pousse vers « non certifié » | Poids |", "|---|---|---|---|"]
    for (n1, p1), (n2, p2) in zip(vers_certifie, vers_non_certifie):
        lignes.append(f"| {n1} | {p1} | {n2} | {p2} |")
    lignes += ["", "## Ce que ces chiffres ne permettent pas de conclure", "",
               "Le modèle reconnaît des listes qui *ressemblent* à celles des produits certifiés. Il ne dit pas si un "
               "produit est meilleur pour la peau ou pour l'environnement, et il ne remplace pas une certification. "
               "Un produit sans label dans Open Beauty Facts n'est pas forcément non certifié : les contributeurs "
               "peuvent avoir oublié de le saisir (voir le journal de nettoyage).", ""]

    DOSSIER_RESULTATS.mkdir(parents=True, exist_ok=True)
    (DOSSIER_RESULTATS / "classifieur_certification.md").write_text("\n".join(lignes), encoding="utf-8")
    sortie = test[["code", "nom", "marque", "cible"]].copy()
    sortie["prediction"] = predictions["Régression logistique (notre modèle)"]
    sortie["probabilite"] = modele.predict_proba(test["ingredients"])[:, 1].round(3)
    sortie.to_csv(DOSSIER_RESULTATS / "classifieur_predictions_test.csv", index=False)
    joblib.dump(modele, FICHIER_MODELE)
    print("\n".join(lignes))


if __name__ == "__main__":
    main()
