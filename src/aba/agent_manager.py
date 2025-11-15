"""Agent management for storage, retrieval, and lifecycle operations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .agent import Agent

# System prompt for the default agent-builder agent
AGENT_BUILDER_SYSTEM_PROMPT = """You are an expert agent designer. You help users:

1. Design new agents by understanding their needs
2. Create agent JSON definitions with appropriate capabilities
3. Generate code scaffolds for agents
4. Refine and improve existing agents

When creating agents, use minimal capabilities by default. Only add capabilities
the agent truly needs.

Available capabilities:
- agent-creation: Create and modify other agents
- file-operations: Read/write files
- code-execution: Run Python/shell commands
- web-access: Search and fetch web content

Most agents should start with NO capabilities and just use the language model for
conversation. Only grant capabilities when the agent's purpose specifically requires them.

When a user asks you to create an agent, use the create_agent tool to write the agent
JSON file. Be thoughtful about which capabilities to grant."""


class AgentManager:
    """Manages agent storage, retrieval, and lifecycle operations."""

    def __init__(self, base_path: Path = Path.home() / ".aba"):
        """Initialize the agent manager.

        Args:
            base_path: Base directory for agent storage (default: ~/.aba)
        """
        self.base_path = base_path
        self.agents_dir = base_path / "agents"
        self.history_dir = base_path / "history"
        self.config_file = base_path / "config.json"

        # Ensure directories exist
        self.agents_dir.mkdir(parents=True, exist_ok=True)
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def load_agent(self, name: str) -> Agent:
        """Load an agent from JSON file.

        Args:
            name: Name of the agent to load

        Returns:
            Agent instance

        Raises:
            FileNotFoundError: If agent does not exist
        """
        agent_file = self.agents_dir / f"{name}.json"
        if not agent_file.exists():
            raise FileNotFoundError(f"Agent '{name}' not found")

        with open(agent_file) as f:
            data = json.load(f)

        return Agent.from_dict(data)

    def save_agent(self, agent: Agent) -> None:
        """Save an agent to JSON file.

        Args:
            agent: Agent instance to save
        """
        agent_file = self.agents_dir / f"{agent.name}.json"
        with open(agent_file, 'w') as f:
            json.dump(agent.to_dict(), f, indent=2)

    def list_agents(self) -> list[str]:
        """List all available agent names.

        Returns:
            List of agent names (sorted)
        """
        return sorted([f.stem for f in self.agents_dir.glob("*.json")])

    def agent_exists(self, name: str) -> bool:
        """Check if an agent exists.

        Args:
            name: Agent name to check

        Returns:
            True if agent exists, False otherwise
        """
        return (self.agents_dir / f"{name}.json").exists()

    def delete_agent(self, name: str) -> None:
        """Delete an agent and its history.

        Args:
            name: Name of agent to delete
        """
        agent_file = self.agents_dir / f"{name}.json"
        history_file = self.history_dir / f"{name}.json"

        if agent_file.exists():
            agent_file.unlink()
        if history_file.exists():
            history_file.unlink()

    def get_last_agent(self) -> Optional[str]:
        """Get the name of the last used agent.

        Returns:
            Agent name or None if no last agent is set
        """
        if not self.config_file.exists():
            return None

        with open(self.config_file) as f:
            config = json.load(f)

        return config.get("last_agent")

    def set_last_agent(self, name: str) -> None:
        """Set the last used agent.

        Args:
            name: Name of agent to set as last used
        """
        config = {}
        if self.config_file.exists():
            with open(self.config_file) as f:
                config = json.load(f)

        config["last_agent"] = name

        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)

    def bootstrap(self) -> Agent:
        """Create the default agent-builder agent.

        This is called on first run to create the meta-agent that can
        create other agents.

        Returns:
            The newly created agent-builder agent
        """
        agent = Agent(
            name="agent-builder",
            description="Meta-agent that helps design and create other agents",
            capabilities=[
                "agent-creation",
                "file-operations",
                "code-execution"
            ],
            system_prompt=AGENT_BUILDER_SYSTEM_PROMPT
        )
        self.save_agent(agent)
        self.set_last_agent("agent-builder")
        return agent
