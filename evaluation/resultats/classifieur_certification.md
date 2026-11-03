# Brique 7 — Reconnaître une liste INCI de produit certifié bio ou naturel

Produit par `python -m evaluation.evaluer_classifieur`.

- Produits dont la réponse est connue : **4791** (410 certifiés, 4381 non certifiés).
- Apprentissage : 3818 produits de 972 marques. Test : **973 produits de 323 autres marques**, jamais vues pendant l'apprentissage (123 certifiés).
- Ingrédients utilisés comme variables (présents dans au moins 5 produits) : 1240.

| Modèle | Exactitude | Précision | Rappel | F1 |
|---|---|---|---|---|
| Régression logistique (notre modèle) | 92.1% | 63.2% | 89.4% | 0.74 |
| Référence : aucun ingrédient synthétique courant → certifié | 58.8% | 23.5% | 100.0% | 0.38 |
| Référence : toujours la classe la plus fréquente | 87.4% | 0.0% | 0.0% | 0.00 |

Précision : parmi les produits annoncés « certifiés », la part qui l'est vraiment. Rappel : parmi les produits vraiment certifiés, la part retrouvée. F1 : moyenne des deux.

## Matrice de confusion de notre modèle

| réel \ prédit | non certifié | certifié |
|---|---|---|
| non certifié | 786 | 64 |
| certifié | 13 | 110 |

## Matrice de confusion de la référence « aucun ingrédient synthétique courant »

| réel \ prédit | non certifié | certifié |
|---|---|---|
| non certifié | 449 | 401 |
| certifié | 0 | 123 |

## Ce que le modèle a appris (les poids les plus forts)

| Pousse vers « certifié » | Poids | Pousse vers « non certifié » | Poids |
|---|---|---|---|
| ALOE BARBADENSIS LEAF JUICE POWDER | 1.82 | SODIUM LAURETH SULFATE | -2.58 |
| CALCIUM HYDROXIDE | 1.74 | PHENOXYETHANOL | -2.32 |
| SPIRULINA PLATENSIS EXTRACT | 1.65 | PANTHENOL | -2.3 |
| TREHALOSE | 1.59 | TOCOPHERYL ACETATE | -2.11 |
| MILK PROTEIN | 1.54 | HEXYL CINNAMAL | -2.0 |
| SODIUM LAUROYL GLUTAMATE | 1.53 | SODIUM SACCHARIN | -2.0 |
| MENTHA PIPERITA LEAF WATER | 1.53 | PROPYLENE GLYCOL | -1.73 |
| SODIUM COCOATE | 1.49 | HYDROXYETHYLCELLULOSE | -1.7 |
| NITROGEN | 1.46 | ALLANTOIN | -1.69 |
| CANANGA ODORATA FLOWER OIL | 1.43 | CAPRYLYL GLYCOL | -1.67 |

## Ce que ces chiffres ne permettent pas de conclure

Le modèle reconnaît des listes qui *ressemblent* à celles des produits certifiés. Il ne dit pas si un produit est meilleur pour la peau ou pour l'environnement, et il ne remplace pas une certification. Un produit sans label dans Open Beauty Facts n'est pas forcément non certifié : les contributeurs peuvent avoir oublié de le saisir (voir le journal de nettoyage).
