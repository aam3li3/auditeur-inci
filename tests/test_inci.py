"""Brique 6 — la lecture des listes INCI, vérifiée sur des exemples écrits à la main."""
import pytest

from src.inci import decouper, enlever_accents, normaliser, traiter_parentheses


def test_enlever_accents():
    assert enlever_accents("Ingrédients : glycérine, eau") == "Ingredients : glycerine, eau"


@pytest.mark.parametrize("brut,attendu", [
    ("  aqua* ", "AQUA"), ("Aloe Vera 20%", "ALOE VERA"), ("CI77891", "CI 77891"),
    ("C.I. 77491", "CI 77491"), ("Glycérine.", "GLYCERINE"), ("Sodium   Chloride", "SODIUM CHLORIDE"),
])
def test_normaliser(brut, attendu):
    assert normaliser(brut) == attendu


def test_parentheses_autre_nom_enleve():
    assert " ".join(traiter_parentheses("AQUA (WATER), BUTYROSPERMUM PARKII (SHEA) BUTTER").split()) == \
        "AQUA , BUTYROSPERMUM PARKII BUTTER"


def test_parentheses_petite_liste_gardee():
    ingredients, _ = decouper("Parfum (Linalool, Limonene), Glycerin")
    assert ingredients == ["PARFUM", "LINALOOL", "LIMONENE", "GLYCERIN"]


def test_virgule_entre_deux_chiffres_ne_coupe_pas():
    ingredients, _ = decouper("Aqua,1,2-Hexanediol, Glycerin")
    assert ingredients == ["AQUA", "1,2-HEXANEDIOL", "GLYCERIN"]


def test_peut_contenir():
    ingredients, peut_contenir = decouper("Ricinus Communis Seed Oil, Cera Alba [+/- CI 77491, CI 15850]")
    assert ingredients == ["RICINUS COMMUNIS SEED OIL", "CERA ALBA"]
    assert peut_contenir == ["CI 77491", "CI 15850"]


def test_entete_et_note_de_bas_de_liste():
    ingredients, _ = decouper("Ingrédients : Aqua, Limonene. *issu de l'agriculture biologique")
    assert ingredients == ["AQUA", "LIMONENE", "ISSU DE L'AGRICULTURE BIOLOGIQUE"]


def test_lire_corrige_les_fautes(lecteur):
    resultat = lecteur.lire("Aqua, Phenoxyetanol, Linalol")
    assert resultat["ingredients"] == ["AQUA", "PHENOXYETHANOL", "LINALOOL"]
    assert ("LINALOL", "LINALOOL") in resultat["corrections"]


def test_lire_synonymes_et_doublons(lecteur):
    resultat = lecteur.lire("Aqua (Water), Eau, Glycérine, Parfum/Fragrance")
    assert resultat["ingredients"] == ["AQUA", "GLYCERIN", "PARFUM"]


def test_on_ne_corrige_pas_un_nom_avec_un_chiffre(lecteur):
    # PEG-41 n'existe pas : surtout ne pas le « corriger » en PEG-40 (on ne change jamais un chiffre).
    assert lecteur.corriger("PEG-41") == (None, "inconnu")


def test_lire_texte_vide(lecteur):
    resultat = lecteur.lire("")
    assert resultat["ingredients"] == [] and resultat["part_reconnue"] == 0.0


def test_part_reconnue(lecteur):
    resultat = lecteur.lire("Eau, glycérine, huile d'amande douce, cire d'abeille")
    assert resultat["part_reconnue"] == 0.5  # EAU et GLYCERINE reconnus, les deux noms français non


@pytest.mark.parametrize("brut,attendu", [("Elaeis Guineensis 0il", "ELAEIS GUINEENSIS OIL"), ("PEG-90M", "PEG-90M"),
                                          ("Acrylates/C10-30 Alkyl Acrylate Crosspolymer",
                                           "ACRYLATES/C10-30 ALKYL ACRYLATE CROSSPOLYMER")])
def test_zero_lu_comme_la_lettre_o(brut, attendu):
    # Le zéro devient O seulement s'il est collé à des lettres et à aucun autre chiffre.
    assert normaliser(brut) == attendu


def test_peg_90m_reste_peg_90m(lecteur):
    assert lecteur.lire("Aqua, PEG-90M")["ingredients"] == ["AQUA", "PEG-90M"]
