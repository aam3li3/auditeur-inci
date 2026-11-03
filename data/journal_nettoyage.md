# Journal de nettoyage

Produit par `python -m src.nettoyage`. Source : Open Beauty Facts (licence ODbL), export `beauty.parquet` du 01/11/2026, extrait par `python -m src.preparer_donnees`.

Export complet : **79138 produits**, dont **22878** avec une liste d'ingrédients (étape 0). Produits gardés à la fin : **14233**.

| # | Étape | Avant | Après | Retirés | Décision |
|---|---|---|---|---|---|
| 1 | Codes-barres en double | 22878 | 22878 | 0 | une seule fiche gardée par code-barres |
| 2 | Lecture des listes INCI | 22878 | 22878 | 0 | 464651 morceaux lus : 345450 noms officiels, 12075 synonymes remplacés (WATER → AQUA…), 6323 doubles noms (« PARFUM/FRAGRANCE »), 10032 fautes corrigées, 90771 non reconnus |
| 3 | Listes illisibles | 22878 | 15412 | 7466 | moins de 80% des morceaux reconnus : liste retirée |
| 4 | Même marque, même formule | 15412 | 14233 | 1179 | un seul produit gardé (souvent le même produit en plusieurs tailles) |
| 5 | Certification | 14233 | 14233 | 0 | 410 certifiés ; 4381 non certifiés (labels renseignés, aucune certification) ; 299 avec une simple mention « bio » ou « naturel » et 9143 sans aucun label : exclus de l'apprentissage |

## Les 15 fautes corrigées le plus souvent

| Écrit sur l'emballage | Nom officiel | Fois |
|---|---|---|
| ALPHA-ISOMETHYL LONONE | ALPHA-ISOMETHYL IONONE | 139 |
| COCO GLUCOSIDE | COCO-GLUCOSIDE | 79 |
| BUTYROSPERMUM PARKI BUTTER | BUTYROSPERMUM PARKII BUTTER | 44 |
| HELIANTHUS ANNUS SEED OIL | HELIANTHUS ANNUUS SEED OIL | 44 |
| PYRIDOXINE HCI | PYRIDOXINE HCL | 42 |
| PARFUMS | PARFUM | 42 |
| LINALOL | LINALOOL | 40 |
| ALUMINIUM CHLOROHYDRATE | ALUMINUM CHLOROHYDRATE | 34 |
| ALPHA ISOMETHYL IONONE | ALPHA-ISOMETHYL IONONE | 31 |
| METHYL PARABEN | METHYLPARABEN | 31 |
| METHYL-2-OCTYNOATE | METHYL 2-OCTYNOATE | 31 |
| SODIUM HYDROXYDE | SODIUM HYDROXIDE | 30 |
| CETEARYLALCOHOL | CETEARYL ALCOHOL | 28 |
| COCOGLUCOSIDE | COCO-GLUCOSIDE | 28 |
| XANTHAM GUM | XANTHAN GUM | 26 |

## Les 15 morceaux non reconnus le plus souvent (exemples de saleté)

| Morceau | Fois |
|---|---|
| SODIUM | 235 |
| IRON OXIDES | 222 |
| YELLOW 5 | 193 |
| NANO | 183 |
| PLEASE REFER TO THE INGREDIENT LIST ON YOUR PRODUCT PACKAGE FOR THE MOST UP TO DATE LIST O | 166 |
| BLUE 1 | 153 |
| ISSUS DE L'AGRICULTURE BIOLOGIQUE | 132 |
| RED 33 | 119 |
| BENEFICIOS | 116 |
| CONSIDERACIONES | 115 |
| PLEASE BE AWARE THAT INGREDIENT LISTS FOR THE PRODUCTS OF OUR BRAND ARE UPDATED REGULARLY | 105 |
| BUTYROSPERMUM PARKII | 104 |
| EXTRACT | 102 |
| 2 | 97 |
| CHLORIDE | 93 |

## Certifications retrouvées dans les labels

| Certification | Produits |
|---|---|
| COSMEBIO | 193 |
| ECOCERT | 88 |
| NATRUE | 53 |
| NATURE ET PROGRES | 28 |
| BDIH | 10 |
| COSMOS ORGANIC | 10 |
| COSMOS | 9 |
| COSMOS NATURAL | 8 |
| ICEA | 6 |
| NATURKOSMETIK CERTIFIEE | 3 |
| SOIL ASSOCIATION | 2 |

## Règles que le fichier ne dit pas, et d'où elles viennent

1. **Un allergène de parfum n'est déclaré qu'au-dessus d'un seuil** : 0,001 % dans un produit non rincé, 0,01 % dans un produit rincé. En dessous, il reste caché dans le mot « PARFUM ». Source : règlement (CE) n° 1223/2009, annexe III, liste complétée par le règlement (UE) 2023/1545 (de 24 à environ 80 substances ; obligatoire pour les produits mis sur le marché depuis le 31/07/2026, et pour tous les produits vendus à partir du 31/07/2028). Conséquence : un allergène absent de la liste ne prouve pas qu'il est absent du produit. La garde (brique 3) en tient compte.
2. **« +/- » ou « may contain » annonce des colorants qui ne sont pas dans toutes les teintes.** Source : règlement (CE) n° 1223/2009, article 19, paragraphe 1, point g). Ces ingrédients sont rangés à part (colonne `peut_contenir`).
3. **L'ordre de la liste a un sens** : les ingrédients sont classés par quantité décroissante, sauf ceux à moins de 1 %. Même source. L'ordre est donc conservé.

## Décisions personnelles (à défendre en soutenance)

- Une liste dont moins de 80% des morceaux sont reconnus est retirée : elle est écrite dans une autre langue, coupée par l'OCR, ou remplacée par un texte (« please refer to the package »).
- Une faute n'est corrigée que si le nom corrigé est très proche (ressemblance ≥ 90 %) et garde exactement les mêmes chiffres : PEG-40 ne devient jamais PEG-60.
- Seuls les organismes certificateurs de cosmétiques comptent (Ecocert, COSMOS, Cosmébio, Natrue, BDIH, ICEA, Nature & Progrès, Soil Association). Une simple mention « bio », « organic » ou « 100 % naturel » est ambiguë : ces produits sont exclus de l'apprentissage, ni positifs ni négatifs.
- Un produit sans aucun label n'est pas forcément non certifié (le contributeur a pu ne pas saisir les labels) : il est exclu de l'apprentissage. Les « non certifiés » sont les produits dont les labels ont été saisis (vegan, sans paraben…) sans aucune certification.

Aucune donnée personnelle : les colonnes qui contiennent des pseudonymes de contributeurs ne sont jamais extraites de l'export.
