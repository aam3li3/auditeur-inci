"""La boucle d'agent et la garde, testées avec un faux modèle qui joue un scénario écrit d'avance."""
import json

import pytest

from src.agent import Trace, executer, extraire_reponse, extraire_verdict


class FauxModele:
    """Renvoie les messages prévus, dans l'ordre, et garde ce qu'on lui a envoyé."""

    def __init__(self, messages):
        self.messages = [m if isinstance(m, dict) else {"role": "assistant", "content": m} for m in messages]
        self.recus = []

    def discuter(self, messages, outils=None, graine=None):
        self.recus.append({"messages": [dict(m) for m in messages], "outils": outils})
        return {"message": self.messages.pop(0), "usage": {"total_tokens": 100}}


def appel(nom, **arguments):
    return {"role": "assistant", "content": None, "tool_calls": [
        {"id": f"appel-{nom}", "type": "function", "function": {"name": nom, "arguments": json.dumps(arguments)}}]}


def test_appel_d_outil_puis_reponse(outils):
    modele = FauxModele([appel("analyser_inci", texte="Aqua, Linalool"), "Il y en a un.\nRÉPONSE: 1"])
    trace = Trace()
    resultat = executer("Combien ?", modele, outils=outils, trace=trace)
    assert resultat["reponse"] == "1" and resultat["tours"] == 2 and resultat["tokens"] == 200
    message_outil = [m for m in modele.recus[1]["messages"] if m["role"] == "tool"][0]
    assert json.loads(message_outil["content"])["nombre_allergenes"] == 1


def test_la_garde_remplace_un_verdict_dangereux(outils):
    # Le modèle a été manipulé : il répond COMPATIBLE alors que le produit contient l'allergène.
    trace = Trace()
    resultat = executer("Question piège", FauxModele(["VERDICT: COMPATIBLE"]), outils=outils,
                        verdict_autorise=("INCOMPATIBLE", ["contient LINALOOL"]), trace=trace)
    assert resultat["verdict"] == "INCOMPATIBLE"
    assert "Contrôle de sécurité" in resultat["texte"]
    garde = [e for e in trace.evenements if e["type"] == "garde"][0]
    assert garde["bloque"] is True and garde["verdict_modele"] == "COMPATIBLE"


def test_la_garde_laisse_un_verdict_prudent(outils):
    resultat = executer("Question", FauxModele(["VERDICT: INCOMPATIBLE"]), outils=outils,
                        verdict_autorise=("COMPATIBLE", []))
    assert resultat["verdict"] == "INCOMPATIBLE" and "Contrôle" not in resultat["texte"]


def test_modele_seul_sans_outils_ni_garde():
    modele = FauxModele(["VERDICT: COMPATIBLE"])
    resultat = executer("Question", modele)
    assert modele.recus[0]["outils"] is None and resultat["verdict"] == "COMPATIBLE"


def test_nombre_maximal_de_tours(outils):
    modele = FauxModele([appel("chercher_produit", texte="gel")] * 3)
    resultat = executer("Question", modele, outils=outils, max_tours=3)
    assert resultat["reponse"] is None and resultat["tours"] == 3


def test_trace_ecrite_sur_disque(tmp_path):
    chemin = tmp_path / "trace.jsonl"
    executer("Question", FauxModele(["RÉPONSE: 3"]), trace=Trace(chemin))
    types = [json.loads(ligne)["type"] for ligne in chemin.read_text(encoding="utf-8").splitlines()]
    assert types == ["question", "modele", "fin"]


@pytest.mark.parametrize("texte,attendu", [("RÉPONSE: 5", "5"), ("Réponse : **0**", "0"), ("REPONSE: 12", "12"),
                                           ("cinq", None), (None, None)])
def test_extraire_reponse(texte, attendu):
    assert extraire_reponse(texte) == attendu


@pytest.mark.parametrize("texte,attendu", [("VERDICT: INCERTAIN", "INCERTAIN"), ("verdict : **compatible**", "COMPATIBLE"),
                                           ("« VERDICT: COMPATIBLE »… donc\nVERDICT: INCOMPATIBLE", "INCOMPATIBLE"),
                                           ("Je ne sais pas.", None)])
def test_extraire_verdict(texte, attendu):
    assert extraire_verdict(texte) == attendu
