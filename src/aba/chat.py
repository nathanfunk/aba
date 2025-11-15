"""Interactive chat helpers for generated agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from .language_model import LanguageModel
from .planning import AgentPlan, CapabilitySuggestion


def _match_capabilities(message: str, capabilities: Iterable[CapabilitySuggestion]) -> list[str]:
    """Return capability summaries that match ``message`` keywords."""

    lowered = message.lower()
    matches: list[str] = []
    for capability in capabilities:
        name = capability.name.lower()
        if name in lowered:
            matches.append(f"{capability.name}: {capability.description}")
    return matches


@dataclass
class AgentChatSession:
    """Very small-text chat interface backed by an ``AgentPlan``."""

    plan: AgentPlan
    language_model: LanguageModel
    history: list[tuple[str, str]] = field(default_factory=list)

    def intro(self) -> str:
        """Return a short welcome message for the session."""

        summary = self.plan.summary or "I turn loose briefs into concrete agent plans."
        capability_names = ", ".join(cap.name for cap in self.plan.capabilities[:3]) or "planning"
        return (
            f"Hi! I'm {self.plan.name}. {summary} "
            f"My focus areas include {capability_names}. Ask me anything about your build."
        )

    def respond(self, message: str) -> str:
        """Generate a deterministic reply for ``message``."""

        self.history.append(("user", message))
        sections: list[str] = []

        if len(self.history) == 1:
            sections.append(self.intro())

        capability_hits = _match_capabilities(message, self.plan.capabilities)
        if capability_hits:
            sections.append("Relevant capabilities:")
            sections.extend(f"- {hit}" for hit in capability_hits)
        else:
            sections.append(
                f"I'll ground the answer using the {len(self.plan.capabilities)} planned capabilities."
            )

        if self.plan.recommended_tools:
            sections.append(
                "Suggested tools: " + ", ".join(self.plan.recommended_tools[:3])
            )

        prompt = (
            f"Agent summary: {self.plan.summary}\n"
            f"Conversation so far: {len(self.history)} turns.\n"
            f"User message: {message}"
        )
        sections.append(self.language_model.complete(prompt))

        response = "\n".join(sections)
        self.history.append(("agent", response))
        return response
