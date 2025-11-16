# Multi-Agent Architecture Implementation Plan

## Overview

Transform ABA from a specialized "agent building tool" into a general agent framework where the agent-builder is just one of many possible agents.

## Core Principles

1. **Minimal by default**: New agents have NO capabilities (just chat with LLM)
2. **Capability-based security**: Each capability must be explicitly granted
3. **Self-bootstrapping**: First run auto-creates `agent-builder` with elevated capabilities
4. **Agent-centric CLI**: Just agent names, no special commands (except `--list`, `--import`, etc.)

## Key Architectural Changes

**Current Code → New Code Mapping:**

| Current | New | Notes |
|---------|-----|-------|
| `AgentBuilderAgent` | `Agent` (with agent-creation capability) | More generic |
| `AgentPlan` | `Agent.capabilities` | Part of agent definition |
| `cli.py` commands | Agent capabilities | `plan`/`materialize` become agent actions |
| `RuleBasedLanguageModel` | `Agent.tools` | Tools available to agent |
| `_run_chat_interface()` | `AgentRuntime.run()` | Generic agent runner |

**New Components Needed:**
1. `Agent` dataclass - represents an agent
2. `AgentManager` - CRUD for agents
3. `AgentRuntime` - runs an agent's chat loop
4. `CapabilityRegistry` - defines what capabilities do
5. `ToolRegistry` - tools agents can use

## Data Model

### Agent JSON Structure

Each agent is a single JSON file:

```json
{
  "name": "agent-builder",
  "description": "An agent that helps you design and create other agents",
  "version": "1.0",
  "created": "2025-11-15T10:00:00Z",
  "last_used": "2025-11-15T15:30:00Z",

  "capabilities": [
    "agent-creation",
    "code-generation",
    "planning"
  ],

  "system_prompt": "You are an expert agent designer. Help users create...",

  "config": {
    "model": "openai/gpt-4o-mini",
    "temperature": 0.7,
    "preserve_history": true
  },

  "tools": [
    "file-operations",
    "json-schema-validator"
  ],

  "metadata": {
    "materialized_path": null,
    "chat_turns": 142
  }
}
```

### Storage Structure

```
~/.aba/
├── config.json                    # {"last_agent": "agent-builder"}
├── agents/
│   ├── agent-builder.json        # The meta-agent
│   ├── research-assistant.json
│   ├── code-reviewer.json
│   └── travel-planner.json
└── history/
    ├── agent-builder.json        # Chat history (separate from agent def)
    ├── research-assistant.json
    └── ...
```

## CLI Interface

### Commands

```bash
# Default: use last agent
$ aba
[agent-builder] You:

# Specify agent by name
$ aba research-assistant
[research-assistant] You:

# Management commands
$ aba --list                    # Show all agents
$ aba --import agent.json       # Import agent
$ aba --export agent-name       # Export agent JSON
$ aba --delete agent-name       # Delete agent

# Override config for session
$ aba --model "openai/gpt-3.5-turbo"
$ aba research-bot --no-history
```

### User Experience Flow

**First Time Setup**
```bash
$ aba
No agents found. Creating default agent-builder...
✓ Created 'agent-builder'

[agent-builder] You: Create a research agent for me
[agent-builder] Agent: I'll help you create a research agent...
```

**Creating New Agents**
```bash
[agent-builder] You: Create a new agent called code-reviewer
[agent-builder] Agent: I'll create that agent for you...
*writes ~/.aba/agents/code-reviewer.json*
✓ Created new agent 'code-reviewer'
```

**Working with Agents**
```bash
$ aba --list
* agent-builder    (last used: 2 hours ago)
  code-reviewer    (last used: never)
  research-bot     (last used: 1 day ago)

$ aba code-reviewer
[code-reviewer] You: Review my auth.py file
```

## Implementation Phases

---

## Phase 1: Core Data Structures

**Estimated time: 3-4 hours**

### 1.1 Agent Definition (`src/aba/agent.py`)

```python
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Agent:
    """A self-contained agent definition."""
    name: str
    description: str
    version: str = "1.0"
    created: str = field(default_factory=lambda: datetime.now().isoformat())
    last_used: str = field(default_factory=lambda: datetime.now().isoformat())

    capabilities: list[str] = field(default_factory=list)  # Empty by default!
    system_prompt: str = ""

    config: dict = field(default_factory=lambda: {
        "model": "openai/gpt-4o-mini",
        "temperature": 0.7,
        "preserve_history": True
    })

    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize to dict for JSON storage."""
        ...

    @classmethod
    def from_dict(cls, data: dict) -> Agent:
        """Deserialize from dict."""
        ...
```

### 1.2 Capability Registry (`src/aba/capabilities.py`)

```python
from dataclasses import dataclass

@dataclass
class Capability:
    """Defines what a capability enables."""
    name: str
    description: str
    tools: list[str]
    system_prompt_addition: str

CAPABILITIES = {
    "agent-creation": Capability(
        name="agent-creation",
        description="Create and modify agent definitions",
        tools=["create_agent", "modify_agent", "delete_agent"],
        system_prompt_addition=(
            "You can create new agents by writing JSON files to ~/.aba/agents/. "
            "New agents should have minimal capabilities by default."
        )
    ),
    "file-operations": Capability(
        name="file-operations",
        description="Read and write files on the local system",
        tools=["read_file", "write_file", "list_files"],
        system_prompt_addition=(
            "You can read and write files using the file operation tools."
        )
    ),
    "code-execution": Capability(
        name="code-execution",
        description="Execute Python and shell commands",
        tools=["exec_python", "exec_shell"],
        system_prompt_addition=(
            "You can execute code using the code execution tools. "
            "Always explain what code will do before executing."
        )
    ),
    "web-access": Capability(
        name="web-access",
        description="Search and fetch web content",
        tools=["web_search", "web_fetch"],
        system_prompt_addition=(
            "You can search the web and fetch content from URLs."
        )
    ),
}
```

### 1.3 Agent Manager (`src/aba/agent_manager.py`)

```python
from pathlib import Path
import json
from typing import Optional
from .agent import Agent
from .capabilities import CAPABILITIES

AGENT_BUILDER_SYSTEM_PROMPT = """You are an expert agent designer. You help users:

1. Design new agents by understanding their needs
2. Create agent JSON definitions with appropriate capabilities
3. Generate code scaffolds for agents
4. Refine and improve existing agents

When creating agents, use minimal capabilities by default. Only add capabilities
the agent truly needs. Available capabilities:
- agent-creation: Create and modify other agents
- file-operations: Read/write files
- code-execution: Run Python/shell commands
- web-access: Search and fetch web content

Most agents should start with NO capabilities and just use the language model."""

class AgentManager:
    """Manages agent storage and retrieval."""

    def __init__(self, base_path: Path = Path.home() / ".aba"):
        self.base_path = base_path
        self.agents_dir = base_path / "agents"
        self.history_dir = base_path / "history"
        self.config_file = base_path / "config.json"

        # Ensure directories exist
        self.agents_dir.mkdir(parents=True, exist_ok=True)
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def load_agent(self, name: str) -> Agent:
        """Load agent from JSON file."""
        agent_file = self.agents_dir / f"{name}.json"
        if not agent_file.exists():
            raise FileNotFoundError(f"Agent '{name}' not found")

        with open(agent_file) as f:
            data = json.load(f)

        return Agent.from_dict(data)

    def save_agent(self, agent: Agent) -> None:
        """Save agent to JSON file."""
        agent_file = self.agents_dir / f"{agent.name}.json"
        with open(agent_file, 'w') as f:
            json.dump(agent.to_dict(), f, indent=2)

    def list_agents(self) -> list[str]:
        """List all agent names."""
        return [f.stem for f in self.agents_dir.glob("*.json")]

    def delete_agent(self, name: str) -> None:
        """Delete an agent and its history."""
        agent_file = self.agents_dir / f"{name}.json"
        history_file = self.history_dir / f"{name}.json"

        if agent_file.exists():
            agent_file.unlink()
        if history_file.exists():
            history_file.unlink()

    def get_last_agent(self) -> Optional[str]:
        """Get the name of the last used agent."""
        if not self.config_file.exists():
            return None

        with open(self.config_file) as f:
            config = json.load(f)

        return config.get("last_agent")

    def set_last_agent(self, name: str) -> None:
        """Set the last used agent."""
        config = {}
        if self.config_file.exists():
            with open(self.config_file) as f:
                config = json.load(f)

        config["last_agent"] = name

        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)

    def bootstrap(self) -> Agent:
        """Create the default agent-builder agent."""
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
```

---

## Phase 2: Agent Runtime

**Estimated time: 4-5 hours**

### 2.1 Tool Registry (`src/aba/tools.py`)

```python
"""Tool implementations for agent capabilities."""
from pathlib import Path
import json
from .agent import Agent
from .agent_manager import AgentManager

def create_agent(name: str, description: str, capabilities: list[str] = None) -> str:
    """Tool: Create a new agent."""
    manager = AgentManager()

    agent = Agent(
        name=name,
        description=description,
        capabilities=capabilities or []
    )

    manager.save_agent(agent)
    return f"Created agent '{name}' with capabilities: {capabilities or []}"

def read_file(path: str) -> str:
    """Tool: Read a file."""
    return Path(path).read_text()

def write_file(path: str, content: str) -> str:
    """Tool: Write a file."""
    Path(path).write_text(content)
    return f"Wrote {len(content)} bytes to {path}"

# Tool registry maps tool names to functions
TOOL_REGISTRY = {
    "create_agent": create_agent,
    "read_file": read_file,
    "write_file": write_file,
    # More tools to be added...
}
```

### 2.2 Agent Runtime (`src/aba/runtime.py`)

```python
"""Runtime for executing agents."""
from .agent import Agent
from .agent_manager import AgentManager
from .capabilities import CAPABILITIES
from .tools import TOOL_REGISTRY
from .language_model import OpenRouterLanguageModel

class AgentRuntime:
    """Runs an agent's chat interface."""

    def __init__(self, agent: Agent, manager: AgentManager):
        self.agent = agent
        self.manager = manager
        self.tools = self._load_tools()
        self.history = self._load_history()
        self.model = self._create_model()

    def _load_tools(self) -> dict:
        """Load tools based on agent capabilities."""
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
        """Build system prompt from base + capabilities."""
        parts = [self.agent.system_prompt] if self.agent.system_prompt else []

        for cap_name in self.agent.capabilities:
            if cap_name in CAPABILITIES:
                parts.append(CAPABILITIES[cap_name].system_prompt_addition)

        return "\n\n".join(parts)

    def _create_model(self):
        """Create language model for this agent."""
        return OpenRouterLanguageModel(
            model=self.agent.config.get("model", "openai/gpt-4o-mini")
        )

    def _load_history(self) -> list:
        """Load chat history if preserve_history is enabled."""
        if not self.agent.config.get("preserve_history", True):
            return []

        history_file = self.manager.history_dir / f"{self.agent.name}.json"
        if history_file.exists():
            import json
            with open(history_file) as f:
                return json.load(f)

        return []

    def _save_history(self) -> None:
        """Save chat history."""
        if not self.agent.config.get("preserve_history", True):
            return

        history_file = self.manager.history_dir / f"{self.agent.name}.json"
        import json
        with open(history_file, 'w') as f:
            json.dump(self.history, f, indent=2)

    def run(self) -> None:
        """Main chat loop."""
        print(f"Starting chat with '{self.agent.name}'")
        if self.agent.description:
            print(f"{self.agent.description}\n")

        if self.agent.capabilities:
            print(f"Capabilities: {', '.join(self.agent.capabilities)}")
        else:
            print("Capabilities: none (chat only)")

        print("Type '/exit' or '/quit' to end the session.\n")

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
                print(f"Error: {exc}")
                self.history.pop()  # Remove user message on error

        self._save_history()
        self.manager.set_last_agent(self.agent.name)

    def _handle_command(self, command: str) -> None:
        """Handle special chat commands."""
        if command == "/capabilities":
            if self.agent.capabilities:
                print(f"Capabilities: {', '.join(self.agent.capabilities)}")
            else:
                print("No capabilities (chat only)")
        elif command == "/clear":
            self.history.clear()
            print("History cleared.")
        else:
            print(f"Unknown command: {command}")

    def _generate_response(self, user_input: str) -> str:
        """Generate response using the language model."""
        system_prompt = self._build_system_prompt()

        # Format conversation history
        conversation = []
        for role, message in self.history[-10:]:  # Last 10 turns
            conversation.append(f"{role.capitalize()}: {message}")

        prompt = f"{system_prompt}\n\n" + "\n".join(conversation)

        return self.model.complete(prompt)
```

---

## Phase 3: New CLI

**Estimated time: 2-3 hours**

### 3.1 Simplified CLI (`src/aba/cli.py`)

```python
"""Command line interface for Agent Builder."""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

from .agent_manager import AgentManager
from .runtime import AgentRuntime

def _list_agents(manager: AgentManager) -> None:
    """List all available agents."""
    agents = manager.list_agents()
    last_agent = manager.get_last_agent()

    if not agents:
        print("No agents found.")
        return

    print("Available agents:")
    for name in sorted(agents):
        prefix = "*" if name == last_agent else " "
        print(f"{prefix} {name}")

def _import_agent(manager: AgentManager, import_file: str) -> None:
    """Import an agent from JSON file."""
    import json
    from .agent import Agent

    with open(import_file) as f:
        data = json.load(f)

    agent = Agent.from_dict(data)
    manager.save_agent(agent)
    print(f"✓ Imported agent '{agent.name}'")

def _export_agent(manager: AgentManager, agent_name: str, output_file: str = None) -> None:
    """Export an agent to JSON file."""
    import json

    agent = manager.load_agent(agent_name)

    if output_file is None:
        output_file = f"{agent_name}.json"

    with open(output_file, 'w') as f:
        json.dump(agent.to_dict(), f, indent=2)

    print(f"✓ Exported agent '{agent_name}' to {output_file}")

def app(argv: list[str] | None = None) -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Agent Builder")

    # Agent selection (positional)
    parser.add_argument(
        "agent",
        nargs="?",
        help="Agent name to run (defaults to last used)"
    )

    # Management flags
    parser.add_argument("--list", action="store_true", help="List all agents")
    parser.add_argument("--import", dest="import_file", help="Import agent from JSON")
    parser.add_argument("--export", help="Export agent to JSON")
    parser.add_argument("--delete", help="Delete an agent")

    # Chat config (available for all agents)
    parser.add_argument("--model", help="Override model for this session")
    parser.add_argument("--no-history", action="store_true", help="Don't load/save history")

    args = parser.parse_args(argv)
    manager = AgentManager()

    # Handle management commands
    if args.list:
        _list_agents(manager)
        return

    if args.import_file:
        _import_agent(manager, args.import_file)
        return

    if args.export:
        output = f"{args.export}.json" if args.agent else None
        _export_agent(manager, args.export, output)
        return

    if args.delete:
        confirm = input(f"Delete agent '{args.delete}'? (y/N): ")
        if confirm.lower() == 'y':
            manager.delete_agent(args.delete)
            print(f"✓ Deleted agent '{args.delete}'")
        return

    # Determine which agent to run
    if args.agent:
        agent_name = args.agent
    else:
        agent_name = manager.get_last_agent()

    # Bootstrap if no agents exist
    agents = manager.list_agents()
    if not agents:
        print("No agents found. Creating default 'agent-builder'...")
        agent = manager.bootstrap()
        print(f"✓ Created '{agent.name}'\n")
    else:
        if agent_name is None:
            agent_name = "agent-builder"  # Fallback to agent-builder

        try:
            agent = manager.load_agent(agent_name)
        except FileNotFoundError:
            print(f"Error: Agent '{agent_name}' not found.")
            print("\nAvailable agents:")
            _list_agents(manager)
            sys.exit(1)

    # Apply config overrides
    if args.model:
        agent.config["model"] = args.model
    if args.no_history:
        agent.config["preserve_history"] = False

    # Run the agent
    runtime = AgentRuntime(agent, manager)
    runtime.run()

if __name__ == "__main__":
    app()
```

---

## Phase 4: Migration & Cleanup

**Estimated time: 2-3 hours**

### 4.1 Code to Remove

- ❌ `AgentBuilderAgent` class
- ❌ `plan` CLI command and related code
- ❌ `materialize` CLI command and related code
- ❌ `chat` CLI subcommand (all interaction is chat now)
- ❌ `_run_chat_interface()` function (replaced by AgentRuntime)
- ❌ `_ChatState` class

### 4.2 Code to Keep/Refactor

- ✅ `AgentPlan` → becomes part of `Agent.metadata` for agent-builder
- ✅ `OpenRouterLanguageModel` → used by runtime
- ✅ `RuleBasedLanguageModel` → becomes a tool for offline agents
- ✅ Planning/inference logic → becomes tool functions for agent-builder
- ✅ `language_model.py` → keep, used by runtime

### 4.3 Files to Update

- `pyproject.toml` - update description if needed
- `README.md` - update with new architecture and commands
- `CLAUDE.md` - update with new architecture

---

## Phase 5: Tools for Agent-Builder

**Estimated time: 3-4 hours**

Implement the planning and materialization logic as tools that agent-builder can use:

### 5.1 Planning Tool

```python
def plan_agent(specification: str) -> dict:
    """
    Analyze specification and suggest agent plan.
    Returns dict with suggested capabilities, tools, etc.
    """
    # Reuse existing inference logic from AgentBuilderAgent
    ...

TOOL_REGISTRY["plan_agent"] = plan_agent
```

### 5.2 Materialization Tool

```python
def materialize_agent(agent_name: str, output_dir: str) -> str:
    """
    Generate code scaffold for an agent.
    Returns path to generated code.
    """
    # Reuse existing materialization logic
    ...

TOOL_REGISTRY["materialize_agent"] = materialize_agent
```

---

## Phase 6: Testing

**Estimated time: 3-4 hours**

### 6.1 Tests to Update

- Update existing tests to work with new architecture
- Test `Agent` serialization/deserialization
- Test `AgentManager` CRUD operations
- Test `AgentRuntime` chat loop (with mocked input)

### 6.2 New Tests to Add

- Test capability loading
- Test tool execution
- Test bootstrap process
- Test agent switching
- Test history persistence

---

## Default Agent-Builder Definition

The auto-created `~/.aba/agents/agent-builder.json`:

```json
{
  "name": "agent-builder",
  "description": "Meta-agent that helps you design and create other agents",
  "version": "1.0",
  "capabilities": [
    "agent-creation",
    "file-operations",
    "code-execution"
  ],
  "system_prompt": "You are an expert agent designer. You help users:\n\n1. Design new agents by understanding their needs\n2. Create agent JSON definitions with appropriate capabilities\n3. Generate code scaffolds for agents\n4. Refine and improve existing agents\n\nWhen creating agents, use minimal capabilities by default. Only add capabilities the agent truly needs.",
  "config": {
    "model": "openai/gpt-4o-mini",
    "temperature": 0.7,
    "preserve_history": true
  },
  "metadata": {}
}
```

---

## Implementation Timeline

```
Phase 1: Data structures (Agent, Capability, AgentManager)     [3-4 hours]
Phase 2: Runtime (AgentRuntime, tool execution)                [4-5 hours]
Phase 3: New CLI (simplified interface)                        [2-3 hours]
Phase 4: Migration (remove old code, refactor)                 [2-3 hours]
Phase 5: Tools for agent-builder (create/materialize)          [3-4 hours]
Phase 6: Testing (update tests, add new ones)                  [3-4 hours]
---
Total estimated: ~20-25 hours
```

## Success Criteria

- [ ] `aba` auto-creates agent-builder on first run
- [ ] `aba agent-name` runs specified agent
- [ ] Agent-builder can create new agents
- [ ] Agents persist across sessions
- [ ] Chat history preserved per agent
- [ ] Minimal agents (no capabilities) work
- [ ] All tests pass
- [ ] Documentation updated
