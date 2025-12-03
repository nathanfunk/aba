"""Runtime for executing agents in chat mode."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from .agent import Agent
from .agent_manager import AgentManager
from .capabilities import CAPABILITIES
from .language_model import OpenRouterLanguageModel
from .tool_schema import ToolSchema
from .tools import TOOL_SCHEMAS


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
        self.tool_schemas = self._load_tools()
        self.history = self._load_history()
        self.model = self._create_model()
        self.current_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def _load_tools(self) -> dict[str, ToolSchema]:
        """Load tool schemas based on agent capabilities.

        Returns:
            Dictionary mapping tool names to ToolSchema objects
        """
        tools = {}

        for capability_name in self.agent.capabilities:
            if capability_name not in CAPABILITIES:
                continue

            capability = CAPABILITIES[capability_name]
            for tool_name in capability.tools:
                if tool_name in TOOL_SCHEMAS:
                    tools[tool_name] = TOOL_SCHEMAS[tool_name]

        # Always include get_context_info tool (informational, always safe)
        if "get_context_info" in TOOL_SCHEMAS:
            tools["get_context_info"] = TOOL_SCHEMAS["get_context_info"]

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

        # Note: With function calling, tool descriptions are in the API request,
        # not the system prompt, so we don't need to list them here

        return "\n\n".join(parts)

    def _build_tools_array(self) -> list[dict]:
        """Build tools array for OpenRouter function calling API.

        Returns:
            List of tool definitions in OpenRouter format
        """
        return [schema.to_openrouter_format() for schema in self.tool_schemas.values()]

    def _create_model(self) -> OpenRouterLanguageModel:
        """Create language model for this agent.

        Returns:
            Configured language model
        """
        return OpenRouterLanguageModel(
            model=self.agent.config.get("model", "openai/gpt-4o-mini"),
            temperature=self.agent.config.get("temperature", 0.7)
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
                user_input = input("> ").strip()
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
                print(f"{self.agent.name}: {response}\n")
                self.history.append(("agent", response))

                # Display token usage
                self._display_usage_info()
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
            if self.tool_schemas:
                print("Available tools:")
                for tool_name in sorted(self.tool_schemas.keys()):
                    print(f"  - {tool_name}")
            else:
                print("No tools available (agent has no capabilities)")
        elif cmd == "/clear":
            self.history.clear()
            print("✓ History cleared.")
        else:
            print(f"Unknown command: {command}")
            print("Type '/help' for available commands.")

    def _display_usage_info(self) -> None:
        """Display token usage and warnings."""
        usage = self.current_usage
        total_tokens = usage.get("total_tokens", 0)

        if total_tokens == 0:
            return

        # Model context window sizes
        context_limits = {
            "openai/gpt-4o": 128000,
            "openai/gpt-4o-mini": 128000,
            "openai/gpt-4-turbo": 128000,
            "openai/gpt-3.5-turbo": 16385,
            "anthropic/claude-3.5-sonnet": 200000,
            "anthropic/claude-3-opus": 200000,
            "anthropic/claude-3-sonnet": 200000,
            "anthropic/claude-3-haiku": 200000,
            "google/gemini-pro": 32768,
            "meta-llama/llama-3-70b-instruct": 8192,
        }

        model = self.agent.config.get("model", "openai/gpt-4o-mini")
        context_limit = context_limits.get(model, 128000)
        usage_percent = (total_tokens / context_limit) * 100

        # Display usage
        print(f"📊 Tokens: {total_tokens:,} / {context_limit:,} ({usage_percent:.1f}%)")

        # Show warnings when approaching limit
        if usage_percent >= 90:
            print("⚠️  WARNING: Approaching context limit! Consider clearing history with /clear")
        elif usage_percent >= 75:
            print("⚠️  Context usage is high. You may want to clear history soon.")

    def _generate_response(self, user_input: str) -> str:
        """Generate response using function calling.

        Args:
            user_input: User's message

        Returns:
            Agent's final response
        """
        # Build messages array for chat API
        messages = []

        # Add system prompt if present
        system_prompt = self._build_system_prompt()
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Add conversation history (last 10 exchanges to avoid context overflow)
        for role, message in self.history[-20:]:
            api_role = "user" if role == "user" else "assistant"
            messages.append({"role": api_role, "content": message})

        # Add current user input
        messages.append({"role": "user", "content": user_input})

        # Build tools array
        tools = self._build_tools_array() if self.tool_schemas else None

        # Tool execution loop
        max_iterations = 10  # Prevent infinite loops
        for iteration in range(max_iterations):
            # Call LLM
            response, usage = self.model.chat(messages, tools=tools)

            # Update usage tracking
            self.current_usage = usage

            # Check if model wants to call tools
            tool_calls = response.get("tool_calls")

            if not tool_calls:
                # No tool calls - return final answer
                content = response.get("content")
                if content:
                    return content
                else:
                    return "(No response from model)"

            # Model wants to call tools - add assistant message to history
            messages.append({
                "role": "assistant",
                "content": response.get("content"),
                "tool_calls": tool_calls
            })

            # Execute each tool call
            for tool_call in tool_calls:
                tool_name = tool_call["function"]["name"]
                tool_args_str = tool_call["function"]["arguments"]
                tool_call_id = tool_call["id"]

                # Execute tool
                try:
                    # Parse arguments
                    tool_args = json.loads(tool_args_str)

                    # Show tool execution to user
                    print(f"\n🔧 Calling tool: {tool_name}")
                    # Show arguments (except _manager which is internal)
                    display_args = {k: v for k, v in tool_args.items() if not k.startswith("_")}
                    if display_args:
                        print(f"   Arguments: {json.dumps(display_args, indent=6)}")

                    # Get tool schema
                    if tool_name not in self.tool_schemas:
                        result = f"Error: Tool '{tool_name}' not found"
                    else:
                        schema = self.tool_schemas[tool_name]

                        # Add _manager parameter for agent management tools
                        if "_manager" in schema.function.__code__.co_varnames:
                            tool_args["_manager"] = self.manager

                        # Add _runtime parameter for context info tools
                        if "_runtime" in schema.function.__code__.co_varnames:
                            tool_args["_runtime"] = self

                        # Call the tool
                        result = schema.function(**tool_args)

                    # Show result to user
                    print(f"   Result: {result}\n")

                except json.JSONDecodeError as e:
                    result = f"Error: Invalid JSON arguments: {e}"
                    print(f"   Result: {result}\n")
                except TypeError as e:
                    result = f"Error: Invalid arguments: {e}"
                    print(f"   Result: {result}\n")
                except Exception as e:
                    result = f"Error executing tool: {e}"
                    print(f"   Result: {result}\n")

                # Add tool result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": str(result)
                })

            # Continue loop to get next response

        # Max iterations reached
        return "(Tool execution limit reached - please try a simpler request)"
