"""Lire une liste d'ingrédients INCI telle qu'elle est écrite sur un emballage (ou recopiée, ou lue par OCR).

Exemple de texte brut :
    "Ingrédients : Aqua (Water), Glycerin, Butyrospermum Parkii (Shea) Butter*, Parfum, Linalol, 1,2-Hexanediol
     [+/- CI 77891, CI 77491]  *issu de l'agriculture biologique"
Ce que l'on veut obtenir :
    ingrédients    : AQUA, GLYCERIN, BUTYROSPERMUM PARKII BUTTER, PARFUM, LINALOOL, 1,2-HEXANEDIOL
    peut contenir  : CI 77891, CI 77491
    corrections    : LINALOL → LINALOOL
    non reconnus   : ISSU DE L'AGRICULTURE BIOLOGIQUE

Deux règles de l'article 19 du règlement (CE) n° 1223/2009 expliquent la forme de ces listes :
  - les ingrédients sont classés par ordre décroissant de quantité (sauf ceux à moins de 1 %) ;
  - pour un produit vendu en plusieurs teintes, les colorants peuvent être annoncés par
    « +/- » ou « may contain » (« peut contenir ») : ils ne sont pas forcément dans chaque teinte.
"""
import difflib
import html
import re
import unicodedata

from src.references import charger_noms_inci, charger_synonymes

# Mots qui annoncent la liste (après passage en majuscules et sans accents)
ENTETE = re.compile(r"^(\s*(INGREDIENTS?|INGREDIENTES|INGREDIENTI|COMPOSITION|INCI|ZUTATEN)\s*[:/.]?\s*)+")

# Ce qui annonce la partie « peut contenir » (teintes)
PEUT_CONTENIR = re.compile(r"\+\s*/\s*[-–]|±|MAY CONTAIN|PEUT CONTENIR|PUEDE CONTENER|KANN ENTHALTEN|PUO CONTENERE")

# Séparateurs entre deux ingrédients :
#  - ; • · | les crochets [ ] et le retour à la ligne ;
#  - la virgule, SAUF entre deux chiffres (« 1,2-HEXANEDIOL » est un seul ingrédient) ;
#  - le tiret entouré d'espaces (« AQUA - GLYCERIN ») ;
#  - le point suivi d'un espace, et l'astérisque précédé d'un espace : ils annoncent souvent
#    une note de bas de liste (« LIMONENE. *issu de l'agriculture biologique »).
SEPARATEURS = re.compile(r"[;•·|\n\[\]]|(?<!\d),|,(?!\d)|\s[-–]\s|\.\s|\s\*")

# Un pourcentage écrit dans la liste (« ALOE VERA 20% »)
POURCENTAGE = re.compile(r"\d+([.,]\d+)?\s*%")


def enlever_accents(texte):
    """« Ingrédients » → « Ingredients » : on décompose chaque lettre et on retire les accents."""
    decompose = unicodedata.normalize("NFKD", texte)
    return "".join(c for c in decompose if not unicodedata.combining(c))


def traiter_parentheses(texte):
    """Entre parenthèses, on trouve :
    - soit un autre nom du même ingrédient : « AQUA (WATER) », « BUTYROSPERMUM PARKII (SHEA) BUTTER »
      → on l'enlève ;
    - soit une petite liste : « PARFUM (LINALOOL, LIMONENE) »
      → on la garde, comme des ingrédients à part (sinon on perdrait des allergènes !)."""
    def remplacer(morceau):
        contenu = morceau.group(1)
        if "," in contenu:
            return ", " + contenu + ", "
        return " "
    return re.sub(r"\(([^()]*)\)", remplacer, texte)


def normaliser(nom):
    """Met un nom d'ingrédient au propre : majuscules, sans accent, sans astérisque, espaces uniques."""
    nom = enlever_accents(nom).upper()
    nom = POURCENTAGE.sub(" ", nom)
    for caractere in "*°†®™[]{}\"“”«»":
        nom = nom.replace(caractere, " ")
    nom = " ".join(nom.split())  # remplace les espaces multiples par un seul
    nom = re.sub(r"\s*/\s*", "/", nom)  # « AQUA / WATER » → « AQUA/WATER »
    nom = ENTETE.sub("", nom)  # un « INGREDIENTS : » peut aussi apparaître au milieu du texte
    nom = nom.strip(" .:-–")
    # Erreur d'OCR : un zéro collé à des lettres, sans autre chiffre à côté, est la lettre O
    # (« ELAEIS GUINEENSIS 0IL » → « … OIL »). Mais dans « PEG-90M », le 0 suit un 9 : c'est un vrai zéro.
    nom = re.sub(r"(?<![0-9])0(?=[A-Z])|(?<=[A-Z])0(?![0-9])", "O", nom)
    # « CI77891 », « C.I. 77891 » ou « CL 77891 » (erreur de lecture I/L) → « CI 77891 » (colorants)
    nom = re.sub(r"^C\.?\s*[IL]\.?\s*(\d{5})$", r"CI \1", nom)
    return nom


def chiffres(nom):
    """Les chiffres d'un nom, dans l'ordre : « PEG-40 » → « 40 »."""
    return "".join(c for c in nom if c.isdigit())


def decouper(texte):
    """Découpe le texte brut en deux listes de noms normalisés : (ingrédients, peut contenir)."""
    texte = html.unescape(texte or "")  # « &amp; » → « & » (le texte vient parfois d'une page web)
    texte = enlever_accents(texte).upper()
    texte = ENTETE.sub("", texte)

    # Tout ce qui suit « +/- » ou « MAY CONTAIN » est la partie « peut contenir ».
    # On la cherche AVANT de traiter les parenthèses, car on trouve souvent « (+/-) ».
    trouve = PEUT_CONTENIR.search(texte)
    if trouve:
        partie_principale = traiter_parentheses(texte[:trouve.start()])
        # on enlève les autres « +/- » ou « MAY CONTAIN » éventuels de la partie « peut contenir »
        partie_peut_contenir = traiter_parentheses(PEUT_CONTENIR.sub(" ", texte[trouve.end():]))
    else:
        partie_principale = traiter_parentheses(texte)
        partie_peut_contenir = ""

    ingredients = []
    for morceau in SEPARATEURS.split(partie_principale):
        nom = normaliser(morceau)
        if nom:
            ingredients.append(nom)
    peut_contenir = []
    for morceau in SEPARATEURS.split(partie_peut_contenir):
        nom = normaliser(morceau)
        if nom:
            peut_contenir.append(nom)
    return ingredients, peut_contenir


class LecteurINCI:
    """Lit des listes INCI. Les listes de référence ne sont chargées qu'une fois, à la création."""

    def __init__(self, noms_inci=None, synonymes=None):
        self.noms_inci = noms_inci if noms_inci is not None else charger_noms_inci()
        self.synonymes = synonymes if synonymes is not None else charger_synonymes()
        # Pour corriger vite, on range les noms connus par première lettre
        self.par_lettre = {}
        for nom in self.noms_inci:
            self.par_lettre.setdefault(nom[0], []).append(nom)
        self.deja_vus = {}  # mémoire des corrections déjà calculées

    def corriger(self, nom):
        """Renvoie (nom officiel ou None, comment on l'a trouvé)."""
        if nom in self.noms_inci:
            return nom, "exact"
        if nom in self.synonymes:
            return self.synonymes[nom], "synonyme"
        if nom in self.deja_vus:
            return self.deja_vus[nom]
        # Deux noms pour le même ingrédient : « PARFUM/FRAGRANCE », « CI 77891/TITANIUM DIOXIDE ».
        # On essaie chaque partie (pas la peine si le nom entier est un nom officiel avec « / »,
        # comme « CAPRYLIC/CAPRIC TRIGLYCERIDE » : il a déjà été trouvé plus haut).
        if "/" in nom:
            for partie in nom.split("/"):
                officiel, _ = self.corriger(partie)
                if officiel is not None:
                    self.deja_vus[nom] = (officiel, "double_nom")
                    return officiel, "double_nom"
        # Une correction ne change jamais un chiffre : PEG-40 et PEG-60 sont deux ingrédients différents,
        # CI 77491 et CI 77492 aussi. Et on ne corrige pas un nom trop court pour être sûr.
        if len(nom) < 6:
            resultat = (None, "inconnu")
        else:
            candidats = []
            for candidat in self.par_lettre.get(nom[0], []):
                if abs(len(candidat) - len(nom)) <= 3 and chiffres(candidat) == chiffres(nom):
                    candidats.append(candidat)
            proches = difflib.get_close_matches(nom, candidats, n=1, cutoff=0.9)
            resultat = (proches[0], "corrige") if proches else (None, "inconnu")
        self.deja_vus[nom] = resultat
        return resultat

    def lire(self, texte):
        """Lit une liste INCI brute et renvoie un dictionnaire avec tout ce qu'on a trouvé."""
        bruts, bruts_peut_contenir = decouper(texte)
        resultat = {"ingredients": [], "peut_contenir": [], "corrections": [], "non_reconnus": [],
                    "comment": {"exact": 0, "synonyme": 0, "double_nom": 0, "corrige": 0, "inconnu": 0}}
        for cle, noms in (("ingredients", bruts), ("peut_contenir", bruts_peut_contenir)):
            for nom in noms:
                officiel, comment = self.corriger(nom)
                resultat["comment"][comment] += 1
                if officiel is None:
                    resultat["non_reconnus"].append(nom)
                    continue
                if comment == "corrige":
                    resultat["corrections"].append((nom, officiel))
                if officiel not in resultat[cle]:  # pas de doublon
                    resultat[cle].append(officiel)
        total = len(bruts) + len(bruts_peut_contenir)
        reconnus = total - len(resultat["non_reconnus"])
        resultat["part_reconnue"] = round(reconnus / total, 3) if total else 0.0
        return resultat
