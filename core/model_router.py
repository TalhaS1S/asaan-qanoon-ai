# core/model_router.py

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List, Optional

import requests
import streamlit as st


# ============================================================
# Provider health state
# ============================================================

@dataclass
class ProviderHealth:
    failures: int = 0
    cooldown_until: float = 0.0
    last_error: str = ""
    last_success: float = 0.0


@st.cache_resource
def get_provider_health() -> Dict[str, ProviderHealth]:
    """
    Persistent provider-health storage.

    @st.cache_resource prevents the health/cooldown information
    from being reset every time Streamlit reruns the script.
    """
    return {
        "openrouter": ProviderHealth(),
        "groq": ProviderHealth(),
        "gemini": ProviderHealth(),
    }


# ============================================================
# Main model router
# ============================================================

class ModelRouter:
    """
    Fault-tolerant AI model router for Asaan Qanoon AI.

    Routing order:

        OpenRouter
            ↓ failure
        Groq
            ↓ failure
        Gemini
            ↓ failure
        Local RAG fallback handled by agents.py
    """

    def __init__(self, secrets):
        self.secrets = secrets
        self.health = get_provider_health()

        # Number of consecutive failures before cooldown.
        self.failure_threshold = 2

        # Cooldown duration in seconds.
        self.cooldown_duration = 120

        # HTTP request timeout.
        self.timeout = 45

    # ========================================================
    # Secrets helper
    # ========================================================

    def _secret(self, key: str, default: str = "") -> str:
        """
        Safely retrieve a value from Streamlit Secrets.
        """

        try:
            value = self.secrets.get(key, default)

            if value is None:
                return default

            return str(value).strip()

        except Exception:
            return default

    # ========================================================
    # Health management
    # ========================================================

    def _available(self, provider: str) -> bool:
        """
        Returns True when provider is not in cooldown.
        """

        health = self.health[provider]

        return time.time() >= health.cooldown_until

    def _fail(self, provider: str, error) -> None:
        """
        Record a provider failure.

        After repeated failures, provider is temporarily skipped.
        """

        health = self.health[provider]

        health.failures += 1

        # Important:
        # Do not store request headers/API keys in errors.
        health.last_error = str(error)[:300]

        if health.failures >= self.failure_threshold:

            health.cooldown_until = (
                time.time() + self.cooldown_duration
            )

    def _success(self, provider: str) -> None:
        """
        Reset provider health after successful response.
        """

        health = self.health[provider]

        health.failures = 0
        health.cooldown_until = 0.0
        health.last_error = ""
        health.last_success = time.time()

    # ========================================================
    # Safe HTTP error helper
    # ========================================================

    def _check_response(
        self,
        response: requests.Response,
        provider: str
    ) -> None:

        status = response.status_code

        if status == 401:
            raise RuntimeError(
                f"{provider}: API authentication failed. "
                "Check the API key in Streamlit Secrets."
            )

        if status == 403:
            raise RuntimeError(
                f"{provider}: request forbidden. "
                "Check API permissions or provider access."
            )

        if status == 404:
            raise RuntimeError(
                f"{provider}: model or API endpoint was not found."
            )

        if status == 429:
            raise RuntimeError(
                f"{provider}: rate limit or free quota reached."
            )

        if status >= 500:
            raise RuntimeError(
                f"{provider}: provider server is temporarily unavailable."
            )

        if not response.ok:

            # Only keep a limited amount of response text.
            # Avoid printing huge error responses.
            message = response.text[:300]

            raise RuntimeError(
                f"{provider}: HTTP {status}: {message}"
            )

    # ========================================================
    # OpenRouter
    # ========================================================

    def _openrouter(
        self,
        messages: List[dict]
    ):

        api_key = self._secret(
            "OPENROUTER_API_KEY"
        )

        model = self._secret(
            "OPENROUTER_MODEL",
            "openrouter/free"
        )

        if not api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not configured."
            )

        if not model:
            model = "openrouter/free"

        url = (
            "https://openrouter.ai/api/v1/"
            "chat/completions"
        )

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.15,
        }

        try:

            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )

        except requests.Timeout:

            raise RuntimeError(
                "OpenRouter request timed out."
            )

        except requests.RequestException as exc:

            raise RuntimeError(
                f"OpenRouter network error: {exc}"
            )

        self._check_response(
            response,
            "OpenRouter"
        )

        try:
            data = response.json()

        except Exception:

            raise RuntimeError(
                "OpenRouter returned invalid JSON."
            )

        choices = data.get(
            "choices",
            []
        )

        if not choices:
            raise RuntimeError(
                "OpenRouter returned no response choices."
            )

        try:

            content = (
                choices[0]
                ["message"]
                ["content"]
            )

        except Exception:

            raise RuntimeError(
                "OpenRouter response format was unexpected."
            )

        if not content:
            raise RuntimeError(
                "OpenRouter returned an empty response."
            )

        # OpenRouter may tell us which actual model was used.
        actual_model = (
            data.get("model")
            or model
        )

        return content, actual_model

    # ========================================================
    # Groq
    # ========================================================

    def _groq(
        self,
        messages: List[dict]
    ):

        api_key = self._secret(
            "GROQ_API_KEY"
        )

        model = self._secret(
            "GROQ_MODEL"
        )

        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not configured."
            )

        if not model:
            raise RuntimeError(
                "GROQ_MODEL is not configured."
            )

        url = (
            "https://api.groq.com/"
            "openai/v1/chat/completions"
        )

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.15,
        }

        try:

            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )

        except requests.Timeout:

            raise RuntimeError(
                "Groq request timed out."
            )

        except requests.RequestException as exc:

            raise RuntimeError(
                f"Groq network error: {exc}"
            )

        self._check_response(
            response,
            "Groq"
        )

        try:
            data = response.json()

        except Exception:

            raise RuntimeError(
                "Groq returned invalid JSON."
            )

        choices = data.get(
            "choices",
            []
        )

        if not choices:

            raise RuntimeError(
                "Groq returned no response choices."
            )

        try:

            content = (
                choices[0]
                ["message"]
                ["content"]
            )

        except Exception:

            raise RuntimeError(
                "Groq response format was unexpected."
            )

        if not content:

            raise RuntimeError(
                "Groq returned an empty response."
            )

        actual_model = (
            data.get("model")
            or model
        )

        return content, actual_model

    # ========================================================
    # Gemini
    # ========================================================

    def _gemini(
        self,
        messages: List[dict]
    ):

        api_key = self._secret(
            "GEMINI_API_KEY"
        )

        model = self._secret(
            "GEMINI_MODEL"
        )

        if not api_key:

            raise RuntimeError(
                "GEMINI_API_KEY is not configured."
            )

        if not model:

            raise RuntimeError(
                "GEMINI_MODEL is not configured."
            )

        # Convert OpenAI-style messages into one text prompt.
        prompt_parts = []

        for message in messages:

            role = message.get(
                "role",
                "user"
            ).upper()

            content = message.get(
                "content",
                ""
            )

            prompt_parts.append(
                f"{role}:\n{content}"
            )

        prompt = "\n\n".join(
            prompt_parts
        )

        url = (
            "https://generativelanguage.googleapis.com/"
            f"v1beta/models/{model}:generateContent"
            f"?key={api_key}"
        )

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.15
            },
        }

        try:

            response = requests.post(
                url,
                headers={
                    "Content-Type":
                    "application/json"
                },
                json=payload,
                timeout=self.timeout,
            )

        except requests.Timeout:

            raise RuntimeError(
                "Gemini request timed out."
            )

        except requests.RequestException as exc:

            raise RuntimeError(
                f"Gemini network error: {exc}"
            )

        self._check_response(
            response,
            "Gemini"
        )

        try:

            data = response.json()

        except Exception:

            raise RuntimeError(
                "Gemini returned invalid JSON."
            )

        candidates = data.get(
            "candidates",
            []
        )

        if not candidates:

            # Gemini may return prompt feedback
            # without a candidate.
            feedback = data.get(
                "promptFeedback",
                {}
            )

            if feedback:

                raise RuntimeError(
                    f"Gemini did not generate a response: "
                    f"{str(feedback)[:250]}"
                )

            raise RuntimeError(
                "Gemini returned no candidates."
            )

        try:

            parts = (
                candidates[0]
                .get(
                    "content",
                    {}
                )
                .get(
                    "parts",
                    []
                )
            )

        except Exception:

            parts = []

        if not parts:

            raise RuntimeError(
                "Gemini returned no content."
            )

        text_parts = []

        for part in parts:

            text = part.get(
                "text"
            )

            if text:
                text_parts.append(
                    text
                )

        content = "\n".join(
            text_parts
        ).strip()

        if not content:

            raise RuntimeError(
                "Gemini returned an empty response."
            )

        return content, model

    # ========================================================
    # Main generation/fallback method
    # ========================================================

    def generate(
        self,
        messages: List[dict],
        preferred_order: Optional[List[str]] = None,
    ):

        """
        Try providers sequentially.

        Expected return format remains compatible
        with core/agents.py:

        {
            "ok": True/False,
            "text": "...",
            "provider": "...",
            "model": "...",
            "errors": [...]
        }
        """

        order = preferred_order or [
            "openrouter",
            "groq",
            "gemini",
        ]

        allowed = {
            "openrouter",
            "groq",
            "gemini",
        }

        errors = []

        for provider in order:

            if provider not in allowed:

                errors.append(
                    f"{provider}: unsupported provider"
                )

                continue

            if not self._available(
                provider
            ):

                remaining = max(
                    0,
                    int(
                        self.health[
                            provider
                        ].cooldown_until
                        - time.time()
                    ),
                )

                errors.append(
                    f"{provider}: cooldown "
                    f"({remaining}s)"
                )

                continue

            try:

                provider_function = getattr(
                    self,
                    f"_{provider}",
                )

                text, model = provider_function(
                    messages
                )

                self._success(
                    provider
                )

                return {
                    "ok": True,
                    "text": text,
                    "provider": provider,
                    "model": model,
                    "errors": errors,
                }

            except Exception as exc:

                self._fail(
                    provider,
                    exc,
                )

                errors.append(
                    f"{provider}: "
                    f"{str(exc)[:250]}"
                )

        # Important:
        # agents.py sees ok=False and activates
        # the local RAG-only fallback.
        return {
            "ok": False,
            "text": "",
            "provider": None,
            "model": None,
            "errors": errors,
        }

    # ========================================================
    # System Health
    # ========================================================

    def status(self):

        """
        Used by streamlit_app.py System Health page.
        """

        now = time.time()

        result = {}

        provider_config = {
            "openrouter": {
                "key":
                    "OPENROUTER_API_KEY",
                "model_key":
                    "OPENROUTER_MODEL",
                "default_model":
                    "openrouter/free",
            },

            "groq": {
                "key":
                    "GROQ_API_KEY",
                "model_key":
                    "GROQ_MODEL",
                "default_model":
                    "",
            },

            "gemini": {
                "key":
                    "GEMINI_API_KEY",
                "model_key":
                    "GEMINI_MODEL",
                "default_model":
                    "",
            },
        }

        for provider, config in provider_config.items():

            health = self.health[
                provider
            ]

            cooldown_seconds = max(
                0,
                int(
                    health.cooldown_until
                    - now
                ),
            )

            api_key = self._secret(
                config["key"]
            )

            model = self._secret(
                config["model_key"],
                config["default_model"],
            )

            result[provider] = {
                "configured":
                    bool(api_key),

                "model":
                    model,

                "healthy":
                    cooldown_seconds == 0,

                "failures":
                    health.failures,

                "cooldown_seconds":
                    cooldown_seconds,

                "last_error":
                    health.last_error,

                "last_success":
                    health.last_success,
            }

        return result

    # ========================================================
    # Optional individual provider test
    # ========================================================

    def test_provider(
        self,
        provider: str
    ):

        """
        Can later be used for Test OpenRouter /
        Test Groq / Test Gemini buttons.
        """

        provider = provider.lower().strip()

        if provider not in {
            "openrouter",
            "groq",
            "gemini",
        }:

            return {
                "ok": False,
                "provider": provider,
                "error":
                    "Unsupported provider.",
            }

        messages = [
            {
                "role": "user",
                "content":
                    "Reply only with: OK",
            }
        ]

        try:

            provider_function = getattr(
                self,
                f"_{provider}",
            )

            text, model = provider_function(
                messages
            )

            self._success(
                provider
            )

            return {
                "ok": True,
                "provider": provider,
                "model": model,
                "text": text,
            }

        except Exception as exc:

            self._fail(
                provider,
                exc,
            )

            return {
                "ok": False,
                "provider": provider,
                "error": str(exc),
            }
