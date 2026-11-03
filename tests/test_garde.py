"""Brique 3 — des tests qui essaient de faire déclarer « compatible » un produit risqué."""
import pytest

from src.garde import appliquer_garde, preparer_allergies, verdict_minimum


def verdict(lecteur, allergenes, texte, allergies):
    return verdict_minimum(lecteur.lire(texte), preparer_allergies(allergies, lecteur), allergenes)


def test_allergene_present_incompatible(lecteur, allergenes):
    v, raisons = verdict(lecteur, allergenes, "Aqua, Glycerin, Linalool", ["linalool"])
    assert v == "INCOMPATIBLE" and raisons == ["contient LINALOOL"]


def test_allergie_mal_orthographiee(lecteur, allergenes):
    # L'utilisatrice écrit « linalol », l'étiquette « Linalool » : ils doivent se retrouver.
    assert verdict(lecteur, allergenes, "Aqua, Linalool", ["linalol"])[0] == "INCOMPATIBLE"


def test_etiquette_mal_orthographiee(lecteur, allergenes):
    assert verdict(lecteur, allergenes, "Aqua, Limonen, Glycerin", ["limonene"])[0] == "INCOMPATIBLE"


def test_allergene_cache_dans_une_parenthese(lecteur, allergenes):
    assert verdict(lecteur, allergenes, "Aqua, Parfum (Linalool, Limonene)", ["limonene"])[0] == "INCOMPATIBLE"


def test_peut_contenir_selon_la_teinte(lecteur, allergenes):
    v, _ = verdict(lecteur, allergenes, "Cera Alba, Ricinus Communis Seed Oil [+/- CI 77491]", ["CI 77491"])
    assert v == "INCERTAIN"


def test_parfum_peut_cacher_un_allergene(lecteur, allergenes):
    # Allergique au linalol, le produit contient PARFUM sans linalol déclaré : on ne peut pas garantir.
    v, raisons = verdict(lecteur, allergenes, "Aqua, Glycerin, Parfum", ["linalool"])
    assert v == "INCERTAIN" and "PARFUM" in raisons[0]


def test_mot_illisible_qui_ressemble_a_l_allergie(lecteur, allergenes):
    v, _ = verdict(lecteur, allergenes, "Aqua, Glycerin, Lnaloolx", ["linalool"])
    assert v == "INCERTAIN"


def test_produit_sans_risque_compatible(lecteur, allergenes):
    v, raisons = verdict(lecteur, allergenes, "Butyrospermum Parkii Butter, Cera Alba", ["linalool"])
    assert v == "COMPATIBLE" and raisons == []


@pytest.mark.parametrize("modele,autorise,final,bloque", [
    ("COMPATIBLE", "INCOMPATIBLE", "INCOMPATIBLE", True),   # le modèle se trompe ou a été manipulé
    ("COMPATIBLE", "INCERTAIN", "INCERTAIN", True),
    ("INCOMPATIBLE", "COMPATIBLE", "INCOMPATIBLE", False),  # le modèle peut être plus prudent
    ("INCERTAIN", "INCERTAIN", "INCERTAIN", False),
    (None, "INCOMPATIBLE", "INCOMPATIBLE", True),           # pas de verdict lisible
])
def test_appliquer_garde(modele, autorise, final, bloque):
    assert appliquer_garde(modele, autorise) == (final, bloque)
