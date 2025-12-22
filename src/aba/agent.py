"""Agent data model for the multi-agent system."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Agent:
    """A self-contained agent definition.

    Agents are minimal by default with no capabilities. Capabilities must be
    explicitly granted to enable file operations, code execution, web access, etc.
    """

    name: str
    description: str
    version: str = "1.0"
    created: str = field(default_factory=lambda: datetime.now().isoformat())
    last_used: str = field(default_factory=lambda: datetime.now().isoformat())

    capabilities: list[str] = field(default_factory=list)
    system_prompt: str = ""

    config: dict = field(default_factory=lambda: {
        "model": "openai/gpt-4o-mini",
        "temperature": 0.7,
        "preserve_history": True
    })

    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize agent to dictionary for JSON storage."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "created": self.created,
            "last_used": self.last_used,
            "capabilities": self.capabilities,
            "system_prompt": self.system_prompt,
            "config": self.config,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Agent:
        """Deserialize agent from dictionary."""
        # Handle capabilities - support both list and legacy string format
        capabilities = data.get("capabilities", [])
        if isinstance(capabilities, str):
            # Legacy format: "cap1,cap2,cap3" -> ["cap1", "cap2", "cap3"]
            capabilities = [c.strip() for c in capabilities.split(",")] if capabilities else []

        return cls(
            name=data["name"],
            description=data["description"],
            version=data.get("version", "1.0"),
            created=data.get("created", datetime.now().isoformat()),
            last_used=data.get("last_used", datetime.now().isoformat()),
            capabilities=capabilities,
            system_prompt=data.get("system_prompt", ""),
            config=data.get("config", {
                "model": "openai/gpt-4o-mini",
                "temperature": 0.7,
                "preserve_history": True
            }),
            metadata=data.get("metadata", {}),
        )
