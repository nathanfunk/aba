# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Agent Builder (aba) is a lightweight multi-agent framework with capability-based permissions. It allows users to create and run specialized AI agents, each with minimal permissions by default.

Key features:
- Multi-agent management (create, run, switch between agents)
- Capability-based security (file-ops, code-exec, web-access, agent-creation)
- Persistent chat history per agent
- Self-bootstrapping (auto-creates agent-builder on first run)
- Simple CLI (just `aba` or `aba agent-name`)

## Architecture

### Core Components

**Agent System:**
- `agent.py` - Agent data model with fields: name, description, version, created, last_used, capabilities, system_prompt, config, metadata
- `agent_manager.py` - CRUD operations (load, save, list, delete agents)
- `capabilities.py` - Capability definitions (what each capability enables)

**Runtime:**
- `runtime.py` - AgentRuntime class that runs agents in chat mode
- `tools.py` - Tool implementations (file ops, code exec, agent creation)
- `language_model.py` - LLM integrations (OpenRouter)

**CLI:**
- `cli.py` - Command-line interface (agent selection, management flags)

### Data Flow

```
aba agent-name
    ↓
CLI loads agent from ~/.aba/agents/agent-name.json
    ↓
AgentRuntime creates runtime with agent + manager
    ↓
Runtime loads tools based on agent.capabilities
    ↓
Chat loop: user input → LLM → response
    ↓
History saved to ~/.aba/history/agent-name.json
```

### Storage Structure

```
~/.aba/
├── config.json              # {"last_agent": "agent-builder"}
├── agents/
│   ├── agent-builder.json   # Meta-agent (can create other agents)
│   └── *.json              # Other agent definitions
└── history/
    └── *.json              # Chat histories (optional, per-agent)
```

## Key Commands

**Running Agents:**
```bash
aba                          # Run last used agent (or bootstrap agent-builder)
aba agent-builder            # Run specific agent
aba --model gpt-4            # Override model for this session
aba --no-history             # Disable history for this session
```

**Managing Agents:**
```bash
aba --list                   # List all agents
aba --export agent-name      # Export agent to JSON
aba --import agent.json      # Import agent from JSON
aba --delete agent-name      # Delete an agent
```

**Development:**
```bash
pip install -e .             # Install in dev mode
pip install -e .[dev]        # Include pytest
pytest                       # Run all tests
pytest -v                    # Verbose output
pytest tests/test_cli.py     # Run specific tests
```

## Agent Capabilities

Agents are **minimal by default** (no capabilities = chat only). Capabilities must be explicitly granted:

- **agent-creation** - Create/modify/delete other agents (agent-builder only by default)
- **file-operations** - Read/write/list/delete files
- **code-execution** - Execute Python and shell commands
- **web-access** - Search web and fetch URLs (placeholder implementation)

Each capability grants access to specific tools (see `capabilities.py`).

## Important Patterns

### 1. Capability-Based Security

Agents only get tools for their declared capabilities:

```python
# Agent with file-operations capability
agent = Agent(
    name="code-reviewer",
    capabilities=["file-operations"]
)
runtime = AgentRuntime(agent, manager)
# runtime.tools will contain: read_file, write_file, list_files, delete_file
```

### 2. Agent Creation Flow

The `agent-builder` agent has `agent-creation` capability, which gives it access to:
- `create_agent(name, description, capabilities, system_prompt)`
- `modify_agent(name, **updates)`
- `delete_agent(name)`
- `list_agents()`

### 3. History Persistence

Each agent can configure history persistence:

```json
{
  "config": {
    "preserve_history": true   // Save/load chat history
  }
}
```

History is stored as JSON in `~/.aba/history/{agent-name}.json`.

### 4. Bootstrap Process

On first run with no agents:
1. CLI detects empty `~/.aba/agents/`
2. Calls `AgentManager.bootstrap()`
3. Creates `agent-builder` with elevated capabilities (agent-creation, file-operations, code-execution)
4. Sets as last-used agent
5. Runs agent-builder in chat mode

## Testing Conventions

- Test files mirror source structure: `tests/test_agent.py` tests `src/aba/agent.py`
- Use pytest fixtures (`tmp_path`) for filesystem tests
- Mock `OpenRouterLanguageModel` for chat tests
- Pass `_manager=test_manager` to tool functions in tests
- All tests should be deterministic (no network calls, no randomness)

Tests are organized across 6 test files (one per main module)

## Module Responsibilities

**agent.py**
- `Agent` dataclass with to_dict/from_dict serialization
- Single source of truth for agent structure
- Fields: name, description, version, created (ISO timestamp), last_used (ISO timestamp), capabilities (list), system_prompt, config (dict), metadata (dict)
- All fields except name and description have sensible defaults

**agent_manager.py**
- `AgentManager` class handles all file I/O for agents
- Bootstrap logic for first-time setup
- Tracks last-used agent in config.json

**capabilities.py**
- `Capability` dataclass defines each capability
- `CAPABILITIES` registry maps names to tools and prompts
- Used by runtime to load tools and build system prompts

**tools.py**
- Tool functions that agents can use
- Each function takes `_manager` param for testability
- Functions return strings (success/error messages)
- Tool registry maps names to functions

**runtime.py**
- `AgentRuntime` class runs the chat loop
- Loads tools based on capabilities
- Builds system prompt from agent.system_prompt + capability additions
- Handles special commands (/help, /capabilities, /tools, /clear)
- Saves/loads history

**cli.py**
- Argument parsing
- Agent selection logic
- Management commands (list, import, export, delete)
- Bootstrap triggering
- Runtime instantiation

## Configuration

**Environment Variables:**
- `OPENROUTER_API_KEY` - Required for chat (get from https://openrouter.ai/keys)

**Agent Config:**
```json
{
  "config": {
    "model": "openai/gpt-4o-mini",  // OpenRouter model ID
    "temperature": 0.7,              // Sampling temperature
    "preserve_history": true         // Save chat history
  }
}
```

## Common Tasks

### Adding a New Capability

1. Add to `CAPABILITIES` in `capabilities.py`
2. Implement tool functions in `tools.py`
3. Add tool names to `TOOL_REGISTRY`
4. Test with an agent that has the capability

### Adding a New Tool

1. Implement function in `tools.py` with `_manager` param
2. Add to `TOOL_REGISTRY`
3. Add tool name to appropriate capability in `capabilities.py`
4. Write tests in `tests/test_tools.py`

### Modifying Agent Structure

1. Update `Agent` dataclass in `agent.py`
2. Update `to_dict()` and `from_dict()` methods
3. Update tests in `tests/test_agent.py`
4. Migration: existing agents will use defaults for new fields

## Security Notes

- Agent-builder is the only agent created with elevated capabilities
- File operations and code execution are opt-in per agent
- Tools accept `_manager` param to prevent using global state
- No tools should execute arbitrary user code without confirmation
- Always validate agent names (no path traversal, special chars, etc.)

## Debugging Tips

**Agent not found:**
```bash
aba --list  # See all agents
ls ~/.aba/agents/  # Check filesystem
```

**Chat errors:**
```bash
echo $OPENROUTER_API_KEY  # Check API key is set
aba --model "openai/gpt-3.5-turbo"  # Try different model
```

**Reset everything:**
```bash
rm -rf ~/.aba
aba  # Starts fresh with new agent-builder
```

**Test a specific component:**
```bash
pytest tests/test_agent_manager.py -v
pytest tests/test_runtime.py::test_runtime_initialization -v
```

## Implementation Notes

- Agents are immutable during runtime (config changes don't persist unless saved)
- History is saved on runtime exit, not continuously
- Last-used agent is set on normal exit only (not on Ctrl+C)
- Tool execution is synchronous (no async/await)
- LLM prompts include last 20 messages (10 exchanges) to avoid context overflow
