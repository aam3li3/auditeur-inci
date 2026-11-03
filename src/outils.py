"""Brique 1 — les outils que le modèle de langage peut appeler.

- chercher_produit(texte) : trouve des produits de la base par leur nom ou leur marque
- analyser_produit(code)  : fiche d'un produit de la base + analyse de sa liste INCI
- analyser_inci(texte)    : analyse d'une liste INCI collée par l'utilisatrice

Le modèle ne lit pas lui-même les listes d'ingrédients : il demande au code de le faire.
"""
import json

from src.references import charger_allergenes, charger_perturbateurs

# Description des outils envoyée au modèle (format « tools » de l'API compatible OpenAI)
SCHEMAS = [
    {"type": "function", "function": {
        "name": "chercher_produit",
        "description": "Cherche des produits cosmétiques dans la base Open Beauty Facts par nom ou par marque. "
                       "Renvoie au plus 5 produits avec leur code.",
        "parameters": {"type": "object", "properties": {
            "texte": {"type": "string", "description": "Nom ou marque, par exemple « gel douche lavande »."}},
            "required": ["texte"]}}},
    {"type": "function", "function": {
        "name": "analyser_produit",
        "description": "Analyse la liste INCI d'un produit de la base, à partir de son code.",
        "parameters": {"type": "object", "properties": {
            "code": {"type": "string", "description": "Le code du produit (code-barres)."}},
            "required": ["code"]}}},
    {"type": "function", "function": {
        "name": "analyser_inci",
        "description": "Analyse une liste d'ingrédients INCI : ingrédients reconnus, allergènes de parfum à "
                       "déclarer (liste européenne), perturbateurs endocriniens potentiels, présence de parfum.",
        "parameters": {"type": "object", "properties": {
            "texte": {"type": "string", "description": "La liste INCI, copiée telle quelle."}},
            "required": ["texte"]}}},
]


class Outils:
    def __init__(self, produits, lecteur, classifieur=None):
        """produits : tableau pandas des produits nettoyés ; lecteur : un LecteurINCI ;
        classifieur : le modèle de la brique 7 (facultatif)."""
        self.produits = produits
        self.lecteur = lecteur
        self.classifieur = classifieur
        self.allergenes = charger_allergenes()
        self.perturbateurs = charger_perturbateurs()

    def analyser_inci(self, texte):
        analyse = self.lecteur.lire(texte)
        ingredients = analyse["ingredients"]
        tous = ingredients + analyse["peut_contenir"]

        allergenes = []
        for nom in tous:
            if nom in self.allergenes:
                fiche = {"nom": nom, "liste": self.allergenes[nom]["liste"]}
                if self.allergenes[nom]["remarque"]:  # par exemple : substance désormais interdite
                    fiche["remarque"] = self.allergenes[nom]["remarque"]
                allergenes.append(fiche)
        perturbateurs = [nom for nom in tous if nom in self.perturbateurs]

        resultat = {
            "nombre_ingredients": len(ingredients),
            "ingredients": ingredients,
            "peut_contenir_selon_teinte": analyse["peut_contenir"],
            "allergenes_a_declarer": allergenes,
            "nombre_allergenes": len(allergenes),
            "perturbateurs_endocriniens_potentiels": perturbateurs,
            "nombre_perturbateurs_potentiels": len(perturbateurs),
            "contient_parfum": "PARFUM" in ingredients or "AROMA" in ingredients,
            "corrections_orthographe": [f"{avant} → {apres}" for avant, apres in analyse["corrections"]],
            "mots_non_reconnus": analyse["non_reconnus"],
        }
        if self.classifieur is not None and ingredients:
            probabilite = self.classifieur.predict_proba(["|".join(ingredients)])[0][1]
            resultat["ressemblance_produits_certifies_bio"] = round(float(probabilite), 2)
        return resultat

    def chercher_produit(self, texte):
        mots = str(texte).lower().split()
        trouves = []
        for produit in self.produits.itertuples():
            fiche = f"{produit.nom} {produit.marque}".lower()
            if mots and all(mot in fiche for mot in mots):
                trouves.append({"code": produit.code, "nom": produit.nom, "marque": produit.marque})
            if len(trouves) == 5:
                break
        return {"recherche": texte, "produits": trouves}

    def analyser_produit(self, code):
        lignes = self.produits[self.produits["code"] == str(code)]
        if lignes.empty:
            raise ValueError(f"aucun produit avec le code {code}")
        produit = lignes.iloc[0]
        fiche = {"code": produit["code"], "nom": produit["nom"], "marque": produit["marque"],
                 "certification_declaree": produit["certification"] or "aucune"}
        return fiche | self.analyser_inci(produit["texte_inci"])

    def executer(self, nom, arguments_json):
        """Exécute un appel demandé par le modèle. Renvoie (texte rendu au modèle, statut)."""
        fonctions = {"chercher_produit": self.chercher_produit, "analyser_produit": self.analyser_produit,
                     "analyser_inci": self.analyser_inci}
        if nom not in fonctions:
            return f"ERREUR : outil inconnu « {nom} ».", "outil_inconnu"
        try:
            arguments = json.loads(arguments_json)
        except (json.JSONDecodeError, TypeError):
            return "ERREUR : arguments illisibles, JSON attendu.", "arguments_invalides"
        try:
            resultat = fonctions[nom](**arguments)
        except TypeError as erreur:  # argument manquant ou en trop
            return f"ERREUR : arguments incorrects ({erreur}).", "erreur"
        except ValueError as erreur:
            return f"ERREUR : {erreur}", "erreur"
        return json.dumps(resultat, ensure_ascii=False), "ok"
