"""Planning primitives for the Agent Building Agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class CapabilitySuggestion:
    """Describes a suggested capability for a target agent."""

    name: str
    description: str
    rationale: str
    priority: str = "medium"


@dataclass
class FileArtifact:
    """Represents a file that should be created for the generated agent."""

    path: str
    description: str
    content: str


@dataclass
class AgentPlan:
    """Structured representation of the agent scaffold to create."""

    name: str
    summary: str
    capabilities: List[CapabilitySuggestion] = field(default_factory=list)
    recommended_tools: List[str] = field(default_factory=list)
    memory_strategy: str | None = None
    conversation_starters: List[str] = field(default_factory=list)

    def capability_table(self) -> str:
        """Return the capability plan as a markdown table for reporting."""

        if not self.capabilities:
            return "No capabilities were inferred."

        header = "| Capability | Priority | Rationale |\n| --- | --- | --- |"
        rows = [
            f"| {cap.name} | {cap.priority} | {cap.rationale} |"
            for cap in self.capabilities
        ]
        return "\n".join([header, *rows])
