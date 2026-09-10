from __future__ import annotations
import time, requests
from dataclasses import dataclass
from typing import Dict

@dataclass
class ProviderHealth:
    failures: int = 0
    cooldown_until: float = 0.0
    last_error: str = ""

class ModelRouter:
    """Fault-tolerant router for free/low-cost model providers."""
    def __init__(self, secrets):
        self.secrets = secrets
        self.health: Dict[str, ProviderHealth] = {
            "openrouter": ProviderHealth(),
            "groq": ProviderHealth(),
            "gemini": ProviderHealth(),
        }

    def _available(self, provider):
        return time.time() >= self.health[provider].cooldown_until

    def _fail(self, provider, err):
        h = self.health[provider]
        h.failures += 1
        h.last_error = str(err)[:300]
        if h.failures >= 2:
            h.cooldown_until = time.time() + 120

    def _success(self, provider):
        self.health[provider] = ProviderHealth()

    def _openrouter(self, messages):
        key = self.secrets.get("OPENROUTER_API_KEY", "")
        model = self.secrets.get("OPENROUTER_MODEL", "openrouter/free")
        if not key: raise RuntimeError("OPENROUTER_API_KEY not configured")
        r = requests.post("https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type":"application/json"},
            json={"model":model,"messages":messages,"temperature":0.15}, timeout=35)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"], model

    def _groq(self, messages):
        key = self.secrets.get("GROQ_API_KEY", "")
        model = self.secrets.get("GROQ_MODEL", "")
        if not key or not model: raise RuntimeError("GROQ credentials/model not configured")
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type":"application/json"},
            json={"model":model,"messages":messages,"temperature":0.15}, timeout=35)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"], model

    def _gemini(self, messages):
        key = self.secrets.get("GEMINI_API_KEY", "")
        model = self.secrets.get("GEMINI_MODEL", "")
        if not key or not model: raise RuntimeError("Gemini credentials/model not configured")
        prompt = "\n\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        r = requests.post(url, headers={"Content-Type":"application/json"},
            json={"contents":[{"parts":[{"text":prompt}]}],
                  "generationConfig":{"temperature":0.15}}, timeout=35)
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"], model

    def generate(self, messages, preferred_order=None):
        order = preferred_order or ["openrouter","groq","gemini"]
        errors=[]
        for provider in order:
            if not self._available(provider):
                continue
            try:
                fn = getattr(self, f"_{provider}")
                text, model = fn(messages)
                self._success(provider)
                return {"ok":True,"text":text,"provider":provider,"model":model,"errors":errors}
            except Exception as e:
                self._fail(provider,e)
                errors.append(f"{provider}: {type(e).__name__}: {str(e)[:150]}")
        return {"ok":False,"text":"","provider":None,"model":None,"errors":errors}

    def status(self):
        now=time.time()
        return {p:{
            "healthy": now >= h.cooldown_until,
            "failures": h.failures,
            "cooldown_seconds": max(0,int(h.cooldown_until-now)),
            "last_error": h.last_error
        } for p,h in self.health.items()}
