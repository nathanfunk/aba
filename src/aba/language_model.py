"""Language model abstractions used by the Agent Building Agent."""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Protocol


class LanguageModel(Protocol):
    """Minimal protocol for LLM-like components used by the agent."""

    def complete(self, prompt: str) -> str:
        """Return a completion for the provided prompt."""


@dataclass
class RuleBasedLanguageModel:
    """A deterministic model used for offline reasoning.

    The implementation is intentionally simple so the repository can be
    executed in offline environments. It mimics a language model by
    generating short, structured responses based on pattern matching.
    """

    temperature: float = 0.0

    def complete(self, prompt: str) -> str:  # noqa: D401 - short description inherited
        prompt_lower = prompt.lower()
        sentences: list[str] = []

        if "tools" in prompt_lower:
            sentences.append(
                "Recommended tools include an HTTP client, JSON parser, and file operations."
            )
        if "memory" in prompt_lower:
            sentences.append(
                "A lightweight JSON file memory will preserve conversation history across runs."
            )
        if "plan" in prompt_lower or "steps" in prompt_lower:
            sentences.append(
                "Key steps: understand the goal, design modular components, and generate skeleton code."
            )

        if not sentences:
            sentences.append(
                "Focus on modular design, explicit interfaces, and testable components."
            )

        return " ".join(sentences)


@dataclass
class OpenRouterLanguageModel:
    """Language model implementation backed by the OpenRouter API."""

    model: str = "openai/gpt-4o-mini"
    temperature: float = 0.7
    api_key_env: str = "OPENROUTER_API_KEY"
    base_url: str = "https://openrouter.ai/api/v1/chat/completions"
    timeout: float = 30.0

    def complete(self, prompt: str) -> str:  # noqa: D401 - protocol short description
        try:
            import requests
        except ModuleNotFoundError as exc:  # pragma: no cover - dependency missing
            raise RuntimeError(
                "The 'requests' package is required to use OpenRouterLanguageModel. "
                "Install it with 'pip install requests'."
            ) from exc

        api_key = os.getenv(self.api_key_env)
        if not api_key:
            raise RuntimeError(
                "OpenRouter API key is required. Set the "
                f"{self.api_key_env!r} environment variable."
            )

        response = requests.post(
            self.base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/anthropics/agent-building-agent",
                "X-Title": "Agent Building Agent",
            },
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self.temperature,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()

        payload = response.json()
        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:  # pragma: no cover - defensive
            raise RuntimeError("Unexpected response payload from OpenRouter") from exc

        if not isinstance(content, str):  # pragma: no cover - defensive
            raise RuntimeError("OpenRouter response did not include text content")

        return content.strip()
