"""Runtime for executing agents in chat mode."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from .agent import Agent
from .agent_manager import AgentManager
from .capabilities import CAPABILITIES
from .language_model import OpenRouterLanguageModel
from .tools import TOOL_REGISTRY


class AgentRuntime:
    """Runs an agent's chat interface with capability-based tool access."""

    def __init__(self, agent: Agent, manager: AgentManager):
        """Initialize the runtime.

        Args:
            agent: Agent to run
            manager: AgentManager instance for persistence
        """
        self.agent = agent
        self.manager = manager
        self.tools = self._load_tools()
        self.history = self._load_history()
        self.model = self._create_model()

    def _load_tools(self) -> dict[str, Callable]:
        """Load tools based on agent capabilities.

        Returns:
            Dictionary mapping tool names to functions
        """
        tools = {}

        for capability_name in self.agent.capabilities:
            if capability_name not in CAPABILITIES:
                continue

            capability = CAPABILITIES[capability_name]
            for tool_name in capability.tools:
                if tool_name in TOOL_REGISTRY:
                    tools[tool_name] = TOOL_REGISTRY[tool_name]

        return tools

    def _build_system_prompt(self) -> str:
        """Build system prompt from agent's base prompt plus capability additions.

        Returns:
            Complete system prompt
        """
        parts = []

        if self.agent.system_prompt:
            parts.append(self.agent.system_prompt)

        for cap_name in self.agent.capabilities:
            if cap_name in CAPABILITIES:
                parts.append(CAPABILITIES[cap_name].system_prompt_addition)

        # Add tool descriptions if agent has capabilities
        if self.tools:
            parts.append("\nAvailable tools:")
            for tool_name in sorted(self.tools.keys()):
                tool_func = self.tools[tool_name]
                doc = tool_func.__doc__ or "No description"
                # Get first line of docstring
                first_line = doc.strip().split("\n")[0]
                parts.append(f"- {tool_name}: {first_line}")

        return "\n\n".join(parts)

    def _create_model(self) -> OpenRouterLanguageModel:
        """Create language model for this agent.

        Returns:
            Configured language model
        """
        return OpenRouterLanguageModel(
            model=self.agent.config.get("model", "openai/gpt-4o-mini")
        )

    def _load_history(self) -> list[tuple[str, str]]:
        """Load chat history if preserve_history is enabled.

        Returns:
            List of (role, message) tuples
        """
        if not self.agent.config.get("preserve_history", True):
            return []

        history_file = self.manager.history_dir / f"{self.agent.name}.json"
        if history_file.exists():
            try:
                with open(history_file) as f:
                    data = json.load(f)
                    return [(item["role"], item["message"]) for item in data]
            except Exception:
                return []

        return []

    def _save_history(self) -> None:
        """Save chat history to file."""
        if not self.agent.config.get("preserve_history", True):
            return

        history_file = self.manager.history_dir / f"{self.agent.name}.json"
        data = [{"role": role, "message": msg} for role, msg in self.history]

        with open(history_file, 'w') as f:
            json.dump(data, f, indent=2)

    def run(self) -> None:
        """Main chat loop."""
        print(f"\nStarting chat with '{self.agent.name}'")

        if self.agent.description:
            print(f"{self.agent.description}")

        if self.agent.capabilities:
            print(f"Capabilities: {', '.join(self.agent.capabilities)}")
        else:
            print("Capabilities: none (chat only)")

        if len(self.history) > 0:
            print(f"Loaded {len(self.history)} previous messages")

        print("Type '/exit' or '/quit' to end the session.")
        print("Type '/help' for available commands.\n")

        while True:
            try:
                user_input = input(f"[{self.agent.name}] You: ").strip()
            except EOFError:
                print()
                break

            if not user_input:
                continue

            if user_input.lower() in {"/exit", "/quit"}:
                print("Exiting chat.")
                break

            # Handle special commands
            if user_input.startswith("/"):
                self._handle_command(user_input)
                continue

            self.history.append(("user", user_input))

            try:
                response = self._generate_response(user_input)
                print(f"[{self.agent.name}] Agent: {response}\n")
                self.history.append(("agent", response))
            except Exception as exc:
                print(f"Error contacting language model: {exc}")
                self.history.pop()  # Remove user message on error

        self._save_history()
        self.manager.set_last_agent(self.agent.name)

    def _handle_command(self, command: str) -> None:
        """Handle special chat commands.

        Args:
            command: Command string (starts with /)
        """
        cmd = command.lower()

        if cmd == "/help":
            print("Available commands:")
            print("  /help         - Show this help")
            print("  /capabilities - Show agent capabilities")
            print("  /tools        - Show available tools")
            print("  /clear        - Clear conversation history")
            print("  /exit, /quit  - Exit chat")
        elif cmd == "/capabilities":
            if self.agent.capabilities:
                print(f"Capabilities: {', '.join(self.agent.capabilities)}")
            else:
                print("No capabilities (chat only)")
        elif cmd == "/tools":
            if self.tools:
                print("Available tools:")
                for tool_name in sorted(self.tools.keys()):
                    print(f"  - {tool_name}")
            else:
                print("No tools available (agent has no capabilities)")
        elif cmd == "/clear":
            self.history.clear()
            print("✓ History cleared.")
        else:
            print(f"Unknown command: {command}")
            print("Type '/help' for available commands.")

    def _generate_response(self, user_input: str) -> str:
        """Generate response using the language model.

        Args:
            user_input: User's message

        Returns:
            Agent's response
        """
        system_prompt = self._build_system_prompt()

        # Format conversation history (last 10 turns to avoid context overflow)
        conversation = []
        for role, message in self.history[-20:]:  # Last 10 exchanges (20 messages)
            conversation.append(f"{role.capitalize()}: {message}")

        # Build the full prompt
        if system_prompt:
            prompt = f"{system_prompt}\n\n---\n\nConversation:\n"
        else:
            prompt = "Conversation:\n"

        prompt += "\n".join(conversation)
        prompt += f"\nAgent:"

        return self.model.complete(prompt)
