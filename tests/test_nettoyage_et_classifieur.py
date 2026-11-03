"""Brique 6 (labels, préparation) et brique 7 (classifieur, mesures), sur des exemples écrits à la main."""
import pandas as pd
import pytest

from evaluation.benchmark import resumer
from src.classifieur import creer_modele, reference_simple
from src.nettoyage import lire_certification
from src.preparer_donnees import joindre, texte_principal
from src.references import lire_csv

MOTIFS = [(ligne["motif"], ligne["certification"]) for ligne in lire_csv("certifications.csv")]


@pytest.mark.parametrize("labels,attendu", [
    ("en:vegan,fr:ecocert-cosmos-organic", ("COSMOS ORGANIC", False)),
    ("fr:cosmetique-bio-charte-cosmebio", ("COSMEBIO", False)),
    ("en:certified-by-ecocert", ("ECOCERT", False)),
    ("en:organic,en:vegan", ("", True)),           # « organic » seul : ambigu
    ("en:100-natural", ("", True)),
    ("en:vegan,en:without-paraben", ("", False)),  # labels saisis, aucune certification
    ("en:non-organic", ("", False)),
    ("en:biodegradable", ("", False)),             # « bio » dans « biodégradable » : pas une mention bio
    ("", ("", False)),
])
def test_lire_certification(labels, attendu):
    assert lire_certification(labels, MOTIFS) == attendu


def test_texte_principal():
    versions = [{"lang": "fr", "text": "Eau, glycérine"}, {"lang": "main", "text": "Aqua, Glycerin"}]
    assert texte_principal(versions, "fr") == "Aqua, Glycerin"
    assert texte_principal([{"lang": "de", "text": ""}, {"lang": "fr", "text": "Eau"}], "fr") == "Eau"
    assert texte_principal(None, "fr") == ""


def test_joindre():
    assert joindre(["en:vegan", "fr:ecocert"]) == "en:vegan,fr:ecocert" and joindre(None) == ""


def test_reference_simple():
    assert reference_simple("AQUA|GLYCERIN|ALOE BARBADENSIS LEAF JUICE") == 1
    assert reference_simple("AQUA|PEG-40 HYDROGENATED CASTOR OIL") == 0
    assert reference_simple("AQUA|DIMETHICONE") == 0


def test_le_classifieur_apprend_un_motif_evident():
    # 20 produits : ceux qui contiennent ALOE sont certifiés, ceux qui contiennent PEG-8 ne le sont pas.
    textes = ["AQUA|ALOE|GLYCERIN"] * 10 + ["AQUA|PEG-8|GLYCERIN"] * 10
    cibles = [1] * 10 + [0] * 10
    modele = creer_modele().fit(textes, cibles)
    assert list(modele.predict(["AQUA|ALOE", "AQUA|PEG-8"])) == [1, 0]


def test_resumer_moyenne_et_dispersion():
    lignes = []
    for lancement, bons in [(1, 2), (2, 3), (3, 4)]:  # 2/4, 3/4 puis 4/4 bonnes réponses
        for i in range(4):
            lignes.append({"mode": "systeme", "type": "allergenes", "lancement": lancement, "correct": i < bons})
    r = resumer(lignes).iloc[0]
    assert r["moyenne"] == pytest.approx(0.75) and r["ecart_type"] == pytest.approx(0.25)
    assert (r["minimum"], r["maximum"], r["lancements"]) == (0.5, 1.0, 3)


def test_les_donnees_propres_n_ont_pas_de_colonne_personnelle():
    colonnes = pd.read_csv("data/brut/produits_bruts.csv.gz", nrows=1).columns
    assert not {"creator", "editors", "last_editor", "photographers"} & set(colonnes)
