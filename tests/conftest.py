"""Données de test inventées, dont toutes les réponses se vérifient à la main."""
import pandas as pd
import pytest

from src.inci import LecteurINCI
from src.outils import Outils
from src.references import charger_allergenes


@pytest.fixture(scope="session")
def lecteur():
    """Un seul lecteur pour tous les tests (le chargement des 24 100 noms prend un peu de temps)."""
    return LecteurINCI()


@pytest.fixture(scope="session")
def allergenes():
    return charger_allergenes()


@pytest.fixture
def produits_jouets():
    lignes = [
        # code,  nom,                      marque,     texte INCI,                                              certification
        ("111", "Gel douche lavande", "Marque A", "Aqua, Sodium Laureth Sulfate, Parfum, Linalool, Limonene", ""),
        ("222", "Baume à lèvres nature", "Marque B", "Butyrospermum Parkii Butter, Cera Alba, Tocopherol", "COSMOS ORGANIC"),
        ("333", "Rouge à lèvres", "Marque A", "Ricinus Communis Seed Oil, Cera Alba [+/- CI 77491, CI 15850]", ""),
        ("444", "Crème solaire", "Marque C", "Aqua, Octocrylene, Homosalate, Propylparaben, Glycerin", ""),
    ]
    return pd.DataFrame(lignes, columns=["code", "nom", "marque", "texte_inci", "certification"])


@pytest.fixture
def outils(produits_jouets, lecteur):
    return Outils(produits_jouets, lecteur)
