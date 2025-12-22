"""Tool implementations for agent capabilities.

Tools are functions that agents can use to interact with the system.
Each capability grants access to specific tools.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from .agent import Agent
from .agent_manager import AgentManager
from .tool_schema import ToolSchema, tool


@tool
def create_agent(
    name: str,
    description: str,
    capabilities: list[str] | None = None,
    system_prompt: str = "",
    _manager: AgentManager | None = None
) -> str:
    """Create a new agent.

    Args:
        name: Agent name (used as filename)
        description: Brief description of what the agent does
        capabilities: List of capability names to grant (default: none)
        system_prompt: Custom system prompt for the agent
        _manager: AgentManager instance (for testing, uses default if None)

    Returns:
        Success message with agent details
    """
    manager = _manager or AgentManager()

    if manager.agent_exists(name):
        return f"Error: Agent '{name}' already exists"

    agent = Agent(
        name=name,
        description=description,
        capabilities=capabilities or [],
        system_prompt=system_prompt
    )

    manager.save_agent(agent)

    caps_str = ", ".join(capabilities) if capabilities else "none (chat only)"
    return f"✓ Created agent '{name}'\nCapabilities: {caps_str}"


@tool
def modify_agent(name: str, _manager: AgentManager | None = None, **updates: Any) -> str:
    """Modify an existing agent's properties.

    Args:
        name: Agent name to modify
        _manager: AgentManager instance (for testing, uses default if None)
        **updates: Fields to update. Supported fields:
            - description: Update agent description
            - capabilities: Update capability list (replaces existing)
            - system_prompt: Update system prompt
            - config: Update configuration (merges with existing)

    Returns:
        Success message confirming the update
    """
    manager = _manager or AgentManager()

    try:
        agent = manager.load_agent(name)
    except FileNotFoundError:
        return f"Error: Agent '{name}' not found"

    # Update fields
    if "description" in updates:
        agent.description = updates["description"]
    if "capabilities" in updates:
        agent.capabilities = updates["capabilities"]
    if "system_prompt" in updates:
        agent.system_prompt = updates["system_prompt"]
    if "config" in updates:
        agent.config.update(updates["config"])

    manager.save_agent(agent)
    return f"✓ Updated agent '{name}'"


@tool
def delete_agent(name: str, _manager: AgentManager | None = None) -> str:
    """Delete an agent.

    Args:
        name: Agent name to delete
        _manager: AgentManager instance (for testing, uses default if None)

    Returns:
        Success message
    """
    manager = _manager or AgentManager()

    if not manager.agent_exists(name):
        return f"Error: Agent '{name}' not found"

    if name == "agent-builder":
        return "Error: Cannot delete the agent-builder"

    manager.delete_agent(name)
    return f"✓ Deleted agent '{name}'"


@tool
def list_agents(_manager: AgentManager | None = None) -> str:
    """List all available agents.

    Args:
        _manager: AgentManager instance (for testing, uses default if None)

    Returns:
        Formatted list of agents
    """
    manager = _manager or AgentManager()
    agents = manager.list_agents()

    if not agents:
        return "No agents found."

    last_agent = manager.get_last_agent()
    lines = ["Available agents:"]

    for name in agents:
        prefix = "*" if name == last_agent else " "
        try:
            agent = manager.load_agent(name)
            caps = f"[{', '.join(agent.capabilities)}]" if agent.capabilities else "[chat only]"
            lines.append(f"{prefix} {name} - {agent.description} {caps}")
        except Exception:
            lines.append(f"{prefix} {name}")

    return "\n".join(lines)


@tool
def get_agent_details(name: str, _manager: AgentManager | None = None) -> str:
    """Get detailed information about a specific agent.

    Args:
        name: Name of the agent to get details for
        _manager: AgentManager instance (for testing, uses default if None)

    Returns:
        Formatted agent details including capabilities and configuration
    """
    manager = _manager or AgentManager()

    try:
        agent = manager.load_agent(name)
    except FileNotFoundError:
        return f"Error: Agent '{name}' not found"
    except Exception as e:
        return f"Error loading agent '{name}': {e}"

    lines = [
        f"Agent: {agent.name}",
        f"Description: {agent.description}",
        f"Created: {agent.created}",
        f"Last used: {agent.last_used}",
        f"Version: {agent.version}",
        "",
        "Capabilities:",
    ]

    if agent.capabilities:
        for cap in agent.capabilities:
            lines.append(f"  - {cap}")
    else:
        lines.append("  (none - chat only)")

    lines.append("")
    lines.append("Configuration:")
    if agent.config:
        for key, value in agent.config.items():
            lines.append(f"  {key}: {value}")
    else:
        lines.append("  (using defaults)")

    if agent.system_prompt:
        lines.append("")
        lines.append("System Prompt:")
        # Truncate long prompts
        prompt_preview = agent.system_prompt[:200]
        if len(agent.system_prompt) > 200:
            prompt_preview += "..."
        lines.append(f"  {prompt_preview}")

    if agent.metadata:
        lines.append("")
        lines.append("Metadata:")
        for key, value in agent.metadata.items():
            lines.append(f"  {key}: {value}")

    return "\n".join(lines)


@tool
def read_file(path: str) -> str:
    """Read contents of a text file.

    Args:
        path: Path to the file to read (absolute or relative)

    Returns:
        File contents as text, or error message if file not found
    """
    try:
        return Path(path).read_text()
    except FileNotFoundError:
        return f"Error: File '{path}' not found"
    except Exception as e:
        return f"Error reading file: {e}"


@tool
def write_file(path: str, content: str) -> str:
    """Write content to a file, creating or overwriting it.

    Args:
        path: Path to the file to write (will be created if it doesn't exist)
        content: Text content to write to the file

    Returns:
        Success message with number of bytes written
    """
    try:
        Path(path).write_text(content)
        return f"✓ Wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error writing file: {e}"


@tool
def list_files(path: str = ".") -> str:
    """List files in a directory.

    Args:
        path: Directory path (default: current directory)

    Returns:
        Formatted list of files
    """
    try:
        dir_path = Path(path)
        if not dir_path.exists():
            return f"Error: Directory '{path}' not found"

        if not dir_path.is_dir():
            return f"Error: '{path}' is not a directory"

        files = sorted(dir_path.iterdir(), key=lambda p: p.name)
        lines = [f"Contents of {path}:"]

        for file in files:
            prefix = "📁" if file.is_dir() else "📄"
            lines.append(f"{prefix} {file.name}")

        return "\n".join(lines)
    except Exception as e:
        return f"Error listing files: {e}"


@tool
def delete_file(path: str) -> str:
    """Delete a file (not directories).

    Args:
        path: Path to the file to delete

    Returns:
        Success message, or error if file not found
    """
    try:
        file_path = Path(path)
        if not file_path.exists():
            return f"Error: File '{path}' not found"

        file_path.unlink()
        return f"✓ Deleted {path}"
    except Exception as e:
        return f"Error deleting file: {e}"


@tool
def exec_python(code: str) -> str:
    """Execute Python code in an isolated subprocess with 10-second timeout.

    Args:
        code: Python code to execute (runs in fresh subprocess, no state persistence)

    Returns:
        Standard output and errors from the code execution
    """
    try:
        result = subprocess.run(
            ["python", "-c", code],
            capture_output=True,
            text=True,
            timeout=10
        )

        output = result.stdout
        if result.stderr:
            output += f"\nErrors:\n{result.stderr}"

        return output or "✓ Code executed (no output)"
    except subprocess.TimeoutExpired:
        return "Error: Code execution timed out (10s limit)"
    except Exception as e:
        return f"Error executing Python code: {e}"


@tool
def exec_shell(command: str) -> str:
    """Execute a shell command with 10-second timeout.

    Args:
        command: Shell command to execute (use with caution - has full shell access)

    Returns:
        Standard output and errors from the command execution
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )

        output = result.stdout
        if result.stderr:
            output += f"\nErrors:\n{result.stderr}"

        return output or "✓ Command executed (no output)"
    except subprocess.TimeoutExpired:
        return "Error: Command execution timed out (10s limit)"
    except Exception as e:
        return f"Error executing shell command: {e}"


@tool
def web_search(query: str) -> str:
    """Search the web for information (NOT YET IMPLEMENTED).

    Args:
        query: Search query to find relevant web pages

    Returns:
        Search results (currently returns placeholder message)
    """
    return f"[Web search not yet implemented for query: {query}]\nThis tool requires implementation with a search API."


@tool
def web_fetch(url: str) -> str:
    """Fetch content from a URL (NOT YET IMPLEMENTED).

    Args:
        url: Full URL to fetch content from (e.g., https://example.com)

    Returns:
        Page content (currently returns placeholder message)
    """
    return f"[Web fetch not yet implemented for URL: {url}]\nThis tool requires implementation with an HTTP client."


@tool
def get_context_info(_runtime: Any = None) -> str:
    """Get information about current context window usage.

    Args:
        _runtime: Runtime instance (auto-injected)

    Returns:
        Context usage information including tokens used and limits
    """
    if _runtime is None:
        return "Error: Runtime context not available"

    # Get usage stats
    usage = _runtime.current_usage
    model = _runtime.agent.config.get("model", "openai/gpt-4o-mini")

    # Model context window sizes (in tokens)
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

    context_limit = context_limits.get(model, 128000)  # Default to 128k

    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    total_tokens = usage.get("total_tokens", 0)

    if total_tokens > 0:
        usage_percent = (total_tokens / context_limit) * 100

        lines = [
            f"Context Window Usage:",
            f"  Model: {model}",
            f"  Context limit: {context_limit:,} tokens",
            f"  Prompt tokens: {prompt_tokens:,}",
            f"  Completion tokens: {completion_tokens:,}",
            f"  Total tokens: {total_tokens:,}",
            f"  Usage: {usage_percent:.1f}%",
            f"  Remaining: {context_limit - total_tokens:,} tokens"
        ]

        return "\n".join(lines)
    else:
        return f"No usage data available yet.\nModel: {model}\nContext limit: {context_limit:,} tokens"


# Tool schemas (decorated functions return ToolSchema objects)
# These contain both the function AND the schema for function calling
TOOL_SCHEMAS: dict[str, ToolSchema] = {
    "create_agent": create_agent,
    "modify_agent": modify_agent,
    "delete_agent": delete_agent,
    "list_agents": list_agents,
    "get_agent_details": get_agent_details,
    "read_file": read_file,
    "write_file": write_file,
    "list_files": list_files,
    "delete_file": delete_file,
    "exec_python": exec_python,
    "exec_shell": exec_shell,
    "web_search": web_search,
    "web_fetch": web_fetch,
    "get_context_info": get_context_info,
}

# Tool registry maps tool names to functions (for backward compatibility)
TOOL_REGISTRY = {
    name: schema.function for name, schema in TOOL_SCHEMAS.items()
}
