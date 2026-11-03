"""Charge en une fois tout ce dont l'agent a besoin : les produits nettoyés, le lecteur INCI et le classifieur."""
import joblib
import pandas as pd

from src.config import FICHIER_MODELE, FICHIER_PROPRE
from src.inci import LecteurINCI
from src.outils import Outils


def charger_outils():
    if not FICHIER_PROPRE.exists():
        raise SystemExit("Données nettoyées absentes : lancez d'abord  python -m src.nettoyage")
    produits = pd.read_csv(FICHIER_PROPRE, dtype={"code": str}, keep_default_na=False)
    classifieur = joblib.load(FICHIER_MODELE) if FICHIER_MODELE.exists() else None
    return Outils(produits, LecteurINCI(), classifieur)
