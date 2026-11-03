"""La boucle d'agent : le modèle répond, appelle des outils si besoin, puis la garde contrôle le verdict.

Deux façons de l'utiliser, pour la comparaison de la brique 9 :
- « systeme »     : Qwen + outils (brique 1) + garde (brique 3)
- « modele_seul » : Qwen seul, même question, sans outil ni garde
Chaque étape est écrite dans une trace (un fichier JSONL : une ligne JSON par événement).
"""
import json
import re
import time
from pathlib import Path

from src.garde import appliquer_garde
from src.llm import sans_reflexion
from src.outils import SCHEMAS

CONSIGNE_SYSTEME = (
    "Tu es un assistant de transparence des ingrédients cosmétiques. Tu disposes d'outils qui lisent les "
    "listes INCI et les comparent aux listes officielles européennes. N'invente jamais la composition d'un "
    "produit et ne compte jamais les ingrédients toi-même : appelle les outils. Ne dis jamais qu'un produit "
    "est « sans danger » : dis seulement ce que contient sa liste déclarée."
)
CONSIGNE_SEUL = "Tu es un assistant de transparence des ingrédients cosmétiques."

MOTIF_REPONSE = re.compile(r"R[ÉE]PONSE\s*:\s*[*_`\s]*(\d+)", re.IGNORECASE)
MOTIF_VERDICT = re.compile(r"VERDICT\s*:\s*[*_`\s]*(COMPATIBLE|INCOMPATIBLE|INCERTAIN)", re.IGNORECASE)


def extraire_reponse(texte):
    """Lit le nombre de la dernière ligne « RÉPONSE: … », ou None."""
    trouvees = MOTIF_REPONSE.findall(texte or "")
    return trouvees[-1] if trouvees else None


def extraire_verdict(texte):
    """Lit le dernier « VERDICT: … », ou None."""
    trouves = MOTIF_VERDICT.findall(texte or "")
    return trouves[-1].upper() if trouves else None


class Trace:
    """Garde chaque événement en mémoire et, si un chemin est donné, l'écrit aussi dans un fichier."""

    def __init__(self, chemin=None):
        self.chemin = Path(chemin) if chemin else None
        self.evenements = []
        if self.chemin:
            self.chemin.parent.mkdir(parents=True, exist_ok=True)
            self.chemin.write_text("", encoding="utf-8")

    def ecrire(self, type_evenement, **donnees):
        evenement = {"t": round(time.time(), 3), "type": type_evenement, **donnees}
        self.evenements.append(evenement)
        if self.chemin:
            with self.chemin.open("a", encoding="utf-8") as f:
                f.write(json.dumps(evenement, ensure_ascii=False, default=str) + "\n")


def executer(question, client, outils=None, verdict_autorise=None, graine=None, trace=None, max_tours=6):
    """Pose une question au modèle et renvoie un dictionnaire avec sa réponse.

    outils           : un objet Outils (mode système) ou None (modèle seul)
    verdict_autorise : (verdict, raisons) calculé par la garde à partir des données, ou None
    """
    trace = trace or Trace()
    avec_outils = outils is not None
    messages = [{"role": "system", "content": CONSIGNE_SYSTEME if avec_outils else CONSIGNE_SEUL},
                {"role": "user", "content": question}]
    trace.ecrire("question", mode="systeme" if avec_outils else "modele_seul", graine=graine, texte=question)
    tokens = 0

    for tour in range(max_tours):
        reponse = client.discuter(messages, outils=SCHEMAS if avec_outils else None, graine=graine)
        message = reponse["message"]
        tokens += reponse["usage"].get("total_tokens", 0)
        appels = (message.get("tool_calls") or []) if avec_outils else []
        trace.ecrire("modele", tour=tour, contenu=message.get("content"), appels=appels)

        if appels:
            # Le modèle demande un ou plusieurs outils : on les exécute et on lui rend les résultats.
            messages.append({"role": "assistant", "content": message.get("content") or "", "tool_calls": appels})
            for appel in appels:
                nom = appel["function"]["name"]
                arguments = appel["function"].get("arguments", "{}")
                resultat, statut = outils.executer(nom, arguments)
                trace.ecrire("outil", nom=nom, arguments=arguments, statut=statut, resultat=resultat)
                messages.append({"role": "tool", "tool_call_id": appel.get("id", nom), "content": resultat})
            continue

        # Le modèle a terminé : on lit sa réponse.
        texte = sans_reflexion(message.get("content"))
        verdict = extraire_verdict(texte)

        # Brique 3 : la garde contrôle le verdict, quoi qu'ait dit le modèle.
        if verdict_autorise is not None:
            verdict_minimum, raisons = verdict_autorise
            verdict_final, bloque = appliquer_garde(verdict, verdict_minimum)
            trace.ecrire("garde", verdict_modele=verdict, verdict_final=verdict_final, bloque=bloque, raisons=raisons)
            if bloque:
                texte += (f"\n\n⚠ Contrôle de sécurité : verdict du modèle « {verdict or 'aucun'} » remplacé par "
                          f"« {verdict_final} » ({' ; '.join(raisons) or 'verdict manquant'}).\nVERDICT: {verdict_final}")
            verdict = verdict_final

        resultat = {"texte": texte, "reponse": extraire_reponse(texte), "verdict": verdict,
                    "tokens": tokens, "tours": tour + 1}
        trace.ecrire("fin", reponse=resultat["reponse"], verdict=verdict, tokens=tokens, tours=tour + 1)
        return resultat

    trace.ecrire("fin", reponse=None, verdict=None, tokens=tokens, tours=max_tours, raison="nombre maximal de tours")
    return {"texte": "", "reponse": None, "verdict": None, "tokens": tokens, "tours": max_tours}
