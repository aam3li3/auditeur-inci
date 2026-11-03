"""Client minimal pour une API compatible OpenAI : llama-server, Ollama ou Cerebras."""
import re
import time

import requests

from src import config


class ClientLLM:
    def __init__(self, url=None, modele=None, cle=None, temperature=None, pause=None, reflexion=None):
        self.url = (url or config.LLM_URL).rstrip("/")
        self.modele = modele or config.LLM_MODELE
        self.cle = cle if cle is not None else config.LLM_CLE
        self.temperature = config.LLM_TEMPERATURE if temperature is None else temperature
        self.pause = config.LLM_PAUSE if pause is None else pause
        self.reflexion = config.LLM_REFLEXION if reflexion is None else reflexion
        self._dernier_appel = 0.0

    def discuter(self, messages, outils=None, graine=None):
        """Un appel au modèle. Renvoie {"message": …, "usage": …}."""
        attente = self.pause - (time.monotonic() - self._dernier_appel)
        if attente > 0:  # limite de débit (compte Cerebras gratuit : 5 requêtes par minute)
            time.sleep(attente)
        corps = {"model": self.modele, "messages": messages, "temperature": self.temperature,
                 "top_p": 0.8, "max_tokens": 2048}
        if not self.reflexion:
            # Désactive le mode « réflexion » (thinking) de Qwen : sinon le modèle peut passer tous ses
            # tokens à réfléchir et rendre une réponse vide. Ollama lit reasoning_effort, llama-server
            # lit chat_template_kwargs ; chaque serveur ignore le champ qui ne le concerne pas.
            corps["reasoning_effort"] = "none"
            corps["chat_template_kwargs"] = {"enable_thinking": False}
        if graine is not None:
            corps["seed"] = graine
        if outils:
            corps["tools"] = outils
        entetes = {"Authorization": f"Bearer {self.cle}"} if self.cle else {}
        reponse = requests.post(f"{self.url}/chat/completions", json=corps, headers=entetes, timeout=600)
        self._dernier_appel = time.monotonic()
        reponse.raise_for_status()
        donnees = reponse.json()
        return {"message": donnees["choices"][0]["message"], "usage": donnees.get("usage") or {}}


def sans_reflexion(texte):
    """Retire un éventuel bloc <think>…</think> (mode « thinking » de Qwen, désactivé par défaut)."""
    return re.sub(r"<think>.*?</think>", "", texte or "", flags=re.S).strip()
