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
    """Modify an existing agent.

    Args:
        name: Agent name to modify
        _manager: AgentManager instance (for testing, uses default if None)
        **updates: Fields to update (description, capabilities, system_prompt, etc.)

    Returns:
        Success message
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
def read_file(path: str) -> str:
    """Read contents of a file.

    Args:
        path: Path to file to read

    Returns:
        File contents
    """
    try:
        return Path(path).read_text()
    except FileNotFoundError:
        return f"Error: File '{path}' not found"
    except Exception as e:
        return f"Error reading file: {e}"


@tool
def write_file(path: str, content: str) -> str:
    """Write content to a file.

    Args:
        path: Path to file to write
        content: Content to write

    Returns:
        Success message with bytes written
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
    """Delete a file.

    Args:
        path: Path to file to delete

    Returns:
        Success message
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
    """Execute Python code.

    Args:
        code: Python code to execute

    Returns:
        Output from code execution
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
    """Execute a shell command.

    Args:
        command: Shell command to execute

    Returns:
        Output from command
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
    """Search the web (placeholder - requires implementation).

    Args:
        query: Search query

    Returns:
        Search results
    """
    return f"[Web search not yet implemented for query: {query}]"


@tool
def web_fetch(url: str) -> str:
    """Fetch content from a URL (placeholder - requires implementation).

    Args:
        url: URL to fetch

    Returns:
        Page content
    """
    return f"[Web fetch not yet implemented for URL: {url}]"


# Tool schemas (decorated functions return ToolSchema objects)
# These contain both the function AND the schema for function calling
TOOL_SCHEMAS: dict[str, ToolSchema] = {
    "create_agent": create_agent,
    "modify_agent": modify_agent,
    "delete_agent": delete_agent,
    "list_agents": list_agents,
    "read_file": read_file,
    "write_file": write_file,
    "list_files": list_files,
    "delete_file": delete_file,
    "exec_python": exec_python,
    "exec_shell": exec_shell,
    "web_search": web_search,
    "web_fetch": web_fetch,
}

# Tool registry maps tool names to functions (for backward compatibility)
TOOL_REGISTRY = {
    name: schema.function for name, schema in TOOL_SCHEMAS.items()
}
