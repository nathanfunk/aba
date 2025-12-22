"""Capability definitions for the agent system.

Capabilities define what agents can do beyond chatting with an LLM.
Each capability grants access to specific tools and adds to the system prompt.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Capability:
    """Defines what a capability enables for an agent."""

    name: str
    description: str
    tools: list[str]
    system_prompt_addition: str


# Registry of all available capabilities
CAPABILITIES = {
    "agent-creation": Capability(
        name="agent-creation",
        description="Create and modify agent definitions",
        tools=["create_agent", "modify_agent", "delete_agent", "list_agents", "get_agent_details"],
        system_prompt_addition=(
            "You can create new agents by specifying their name, description, and capabilities. "
            "New agents should have minimal capabilities by default - only add what they truly need. "
            "Use the create_agent tool to create new agents as JSON files.\n\n"
            "Available capabilities to grant agents:\n"
            "- agent-creation: Create and modify other agents\n"
            "- file-operations: Read and write files\n"
            "- code-execution: Execute Python and shell commands\n"
            "- web-access: Search and fetch web content\n\n"
            "Most agents should start with NO capabilities and just use the language model for chat.\n\n"
            "IMPORTANT: These tools only manage agent definition files. You CANNOT switch to or run "
            "other agents from within this chat session. If the user wants to use a different agent, "
            "they must exit this session and run `aba <agent-name>` from the command line."
        )
    ),
    "file-operations": Capability(
        name="file-operations",
        description="Read and write files on the local system",
        tools=["read_file", "write_file", "list_files", "delete_file"],
        system_prompt_addition=(
            "You can read and write files using the file operation tools. "
            "Always be careful when writing files - explain what you're doing and ask for confirmation "
            "if the operation might be destructive."
        )
    ),
    "code-execution": Capability(
        name="code-execution",
        description="Execute Python and shell commands",
        tools=["exec_python", "exec_shell"],
        system_prompt_addition=(
            "You can execute Python code and shell commands using the code execution tools. "
            "Always explain what code will do before executing it. "
            "Never execute destructive commands without explicit user confirmation."
        )
    ),
    "web-access": Capability(
        name="web-access",
        description="Search and fetch web content",
        tools=["web_search", "web_fetch"],
        system_prompt_addition=(
            "You can search the web and fetch content from URLs using the web access tools. "
            "This is useful for gathering information, researching topics, or checking documentation."
        )
    ),
}
