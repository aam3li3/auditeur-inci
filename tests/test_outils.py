"""Brique 1 — les trois outils appelés par le modèle, sur des produits inventés."""
import json

import pytest


def test_analyser_inci_compte_les_allergenes(outils):
    resultat = outils.analyser_inci("Aqua, Parfum, Linalool, Limonene, Lavandula Angustifolia Oil, Glycerin")
    noms = [a["nom"] for a in resultat["allergenes_a_declarer"]]
    assert noms == ["LINALOOL", "LIMONENE", "LAVANDULA ANGUSTIFOLIA OIL"]
    assert resultat["nombre_allergenes"] == 3 and resultat["contient_parfum"] is True


def test_allergene_ajoute_en_2023(outils):
    resultat = outils.analyser_inci("Aqua, Menthol, Vanillin")
    assert [a["liste"] for a in resultat["allergenes_a_declarer"]] == ["2023/1545", "2023/1545"]


def test_allergene_interdit_signale(outils):
    resultat = outils.analyser_inci("Aqua, Butylphenyl Methylpropional")
    assert "interdite" in resultat["allergenes_a_declarer"][0]["remarque"]


def test_analyser_inci_perturbateurs_potentiels(outils):
    resultat = outils.analyser_inci("Aqua, Octocrylene, Homosalate, Propylparaben, Glycerin")
    assert resultat["perturbateurs_endocriniens_potentiels"] == ["OCTOCRYLENE", "HOMOSALATE", "PROPYLPARABEN"]


def test_peut_contenir_compte_aussi(outils):
    resultat = outils.analyser_inci("Cera Alba [+/- Benzyl Benzoate]")
    assert resultat["peut_contenir_selon_teinte"] == ["BENZYL BENZOATE"] and resultat["nombre_allergenes"] == 1


def test_chercher_produit(outils):
    # Tous les mots cherchés doivent apparaître dans le nom ou la marque, en minuscules ou majuscules.
    assert [p["code"] for p in outils.chercher_produit("Rouge marque")["produits"]] == ["333"]
    assert [p["code"] for p in outils.chercher_produit("lavande")["produits"]] == ["111"]
    assert outils.chercher_produit("introuvable")["produits"] == []


def test_analyser_produit(outils):
    fiche = outils.analyser_produit("222")
    assert fiche["certification_declaree"] == "COSMOS ORGANIC" and fiche["nombre_allergenes"] == 0


def test_executer_appel_valide(outils):
    texte, statut = outils.executer("analyser_produit", json.dumps({"code": "111"}))
    assert statut == "ok" and json.loads(texte)["nombre_allergenes"] == 2


@pytest.mark.parametrize("nom,arguments,statut", [
    ("analyser_produit", "{pas du json", "arguments_invalides"),
    ("supprimer_produit", "{}", "outil_inconnu"),
    ("analyser_produit", json.dumps({"code": "999"}), "erreur"),
    ("analyser_inci", json.dumps({}), "erreur"),
    ("analyser_inci", json.dumps({"texte": "Aqua", "en_trop": 1}), "erreur"),
])
def test_executer_appels_defectueux(outils, nom, arguments, statut):
    assert outils.executer(nom, arguments)[1] == statut
