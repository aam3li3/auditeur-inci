"""Le client HTTP : on vérifie la requête envoyée, sans serveur (requests.post est remplacé)."""
import pytest

from src import llm
from src.llm import ClientLLM, sans_reflexion


class FausseReponse:
    def raise_for_status(self):
        pass

    def json(self):
        return {"choices": [{"message": {"role": "assistant", "content": "ok"}}], "usage": {"total_tokens": 7}}


@pytest.fixture
def envois(monkeypatch):
    captures = []

    def faux_post(url, json, headers, timeout):
        captures.append({"url": url, "corps": json, "entetes": headers})
        return FausseReponse()

    monkeypatch.setattr(llm.requests, "post", faux_post)
    return captures


def test_requete_avec_outils_et_graine(envois):
    client = ClientLLM(url="http://serveur/v1/", modele="m", cle="", temperature=0.7, pause=0)
    reponse = client.discuter([{"role": "user", "content": "x"}], outils=[{"type": "function"}], graine=3)
    envoi = envois[0]
    assert envoi["url"] == "http://serveur/v1/chat/completions"
    assert envoi["corps"]["seed"] == 3 and envoi["corps"]["tools"] == [{"type": "function"}]
    assert envoi["entetes"] == {}  # pas de clé en local
    assert reponse["usage"]["total_tokens"] == 7


def test_cle_dans_l_entete_seulement(envois):
    ClientLLM(url="http://serveur/v1", modele="m", cle="secret", pause=0).discuter([])
    assert envois[0]["entetes"] == {"Authorization": "Bearer secret"}
    assert "secret" not in str(envois[0]["corps"])


def test_sans_outils_pas_de_champ_tools(envois):
    ClientLLM(url="http://serveur/v1", modele="m", cle="", pause=0).discuter([])
    assert "tools" not in envois[0]["corps"] and "seed" not in envois[0]["corps"]


def test_sans_reflexion():
    assert sans_reflexion("<think>long\nraisonnement</think>\nRÉPONSE: NUL") == "RÉPONSE: NUL"
    assert sans_reflexion(None) == ""


def test_reflexion_desactivee_par_defaut(envois):
    ClientLLM(url="http://serveur/v1", modele="m", cle="", pause=0, reflexion=False).discuter([])
    assert envois[0]["corps"]["reasoning_effort"] == "none"
    assert envois[0]["corps"]["chat_template_kwargs"] == {"enable_thinking": False}


def test_reflexion_activee_sur_demande(envois):
    ClientLLM(url="http://serveur/v1", modele="m", cle="", pause=0, reflexion=True).discuter([])
    assert "reasoning_effort" not in envois[0]["corps"]
