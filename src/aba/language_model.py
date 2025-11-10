"""Language model abstractions used by the Agent Building Agent."""

from __future__ import annotations

from dataclasses import dataclass
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
