import time
import requests
import streamlit as st


class ProviderHealth:
    def __init__(self):
        self.failures = {}
        self.cooldowns = {}

    def is_available(self, provider):
        until = self.cooldowns.get(provider, 0)
        return time.time() >= until

    def mark_success(self, provider):
        self.failures[provider] = 0
        self.cooldowns[provider] = 0

    def mark_failure(self, provider):
        count = self.failures.get(provider, 0) + 1
        self.failures[provider] = count

        if count >= 2:
            self.cooldowns[provider] = time.time() + 120


@st.cache_resource
def get_provider_health():
    return ProviderHealth()


class ModelRouter:
    def __init__(self, secrets):
        self.secrets = secrets
        self.health = get_provider_health()

    def _get_secret(self, key, default=""):
        try:
            return self.secrets.get(key, default)
        except Exception:
            return default

    def _openrouter(self, messages):
        api_key = self._get_secret("OPENROUTER_API_KEY")
        model = self._get_secret("OPENROUTER_MODEL", "openrouter/free")

        if not api_key:
            raise RuntimeError("OpenRouter API key is missing.")

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
            },
            timeout=45,
        )

        if response.status_code == 429:
            raise RuntimeError("OpenRouter rate limit reached.")

        response.raise_for_status()

        data = response.json()

        if "choices" not in data or not data["choices"]:
            raise RuntimeError("OpenRouter returned no choices.")

        content = data["choices"][0]["message"].get("content", "")

        if not content:
            raise RuntimeError("OpenRouter returned an empty response.")

        return {
            "text": content,
            "provider": "openrouter",
            "model": model,
        }

    def _groq(self, messages):
        api_key = self._get_secret("GROQ_API_KEY")
        model = self._get_secret("GROQ_MODEL")

        if not api_key:
            raise RuntimeError("Groq API key is missing.")

        if not model:
            raise RuntimeError("Groq model is missing.")

        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
            },
            timeout=45,
        )

        if response.status_code == 429:
            raise RuntimeError("Groq rate limit reached.")

        response.raise_for_status()

        data = response.json()

        if "choices" not in data or not data["choices"]:
            raise RuntimeError("Groq returned no choices.")

        content = data["choices"][0]["message"].get("content", "")

        if not content:
            raise RuntimeError("Groq returned an empty response.")

        return {
            "text": content,
            "provider": "groq",
            "model": model,
        }

    def _gemini(self, messages):
        api_key = self._get_secret("GEMINI_API_KEY")
        model = self._get_secret("GEMINI_MODEL")

        if not api_key:
            raise RuntimeError("Gemini API key is missing.")

        if not model:
            raise RuntimeError("Gemini model is missing.")

        prompt = "\n\n".join(
            f"{msg.get('role', 'user').upper()}: {msg.get('content', '')}"
            for msg in messages
        )

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={api_key}"
        )

        response = requests.post(
            url,
            headers={
                "Content-Type": "application/json",
            },
            json={
                "contents": [
                    {
                        "parts": [
                            {
                                "text": prompt
                            }
                        ]
                    }
                ]
            },
            timeout=45,
        )

        if response.status_code == 429:
            raise RuntimeError("Gemini rate limit reached.")

        response.raise_for_status()

        data = response.json()

        candidates = data.get("candidates", [])

        if not candidates:
            raise RuntimeError("Gemini returned no candidates.")

        parts = (
            candidates[0]
            .get("content", {})
            .get("parts", [])
        )

        if not parts:
            raise RuntimeError("Gemini returned no content.")

        content = parts[0].get("text", "")

        if not content:
            raise RuntimeError("Gemini returned an empty response.")

        return {
            "text": content,
            "provider": "gemini",
            "model": model,
        }

    def generate(self, messages):
        providers = [
            ("openrouter", self._openrouter),
            ("groq", self._groq),
            ("gemini", self._gemini),
        ]

        errors = []

        for provider_name, provider_fn in providers:

            if not self.health.is_available(provider_name):
                errors.append(
                    f"{provider_name}: temporarily in cooldown"
                )
                continue

            try:
                result = provider_fn(messages)

                self.health.mark_success(provider_name)

                result["errors"] = errors

                return result

            except Exception as e:
                self.health.mark_failure(provider_name)

                errors.append(
                    f"{provider_name}: {str(e)}"
                )

        return {
            "text": "",
            "provider": "none",
            "model": "none",
            "errors": errors,
        }
