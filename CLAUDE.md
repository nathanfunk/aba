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
- `runtime.py` - AgentRuntime class that runs agents with function calling
- `tools.py` - Tool implementations decorated with @tool for schema generation
- `tool_schema.py` - Tool decorator and schema system (inspired by LangChain)
- `language_model.py` - LLM integrations (OpenRouter with function calling support)

**CLI:**
- `cli.py` - Command-line interface (agent selection, management flags)

**Web Interface:**
- `web/server.py` - FastAPI application with REST API and WebSocket endpoints
- `web/agent_session.py` - Async agent runtime for web (non-blocking tool execution)
- `web/streaming_model.py` - OpenRouter SSE streaming client (parses Server-Sent Events)
- `web/messages.py` - WebSocket protocol message definitions
- `web/static/` - Built React frontend (served by FastAPI)

### Data Flow

**CLI Flow:**
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

**Web Interface Flow:**
```
User opens http://localhost:8000
    ↓
FastAPI serves React UI from web/static/
    ↓
User selects agent → WebSocket connects to /ws/chat/{agent_name}
    ↓
AgentSession loads agent and tools based on capabilities
    ↓
User sends message via WebSocket
    ↓
AgentSession.handle_user_message() processes message
    ↓
StreamingModel.chat_stream() calls OpenRouter API with SSE
    ↓
Server streams chunks to client in real-time:
  - stream_chunk: partial text responses
  - tool_call: when agent invokes a tool
  - tool_result: tool execution output
  - stream_complete: response finished
    ↓
History saved to ~/.aba/history/{agent-name}.json on disconnect
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

**Running Agents (CLI):**
```bash
aba                          # Run last used agent (or bootstrap agent-builder)
aba agent-builder            # Run specific agent
aba --model gpt-4            # Override model for this session
aba --no-history             # Disable history for this session
```

**Running Web Interface:**
```bash
source venv/bin/activate     # Activate virtual environment
python -m aba.web.server     # Start web server on port 8000
# Or: aba-web (if installed with entry point)
# Access at: http://localhost:8000
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

## Function Calling Architecture

aba uses OpenRouter's function calling API for structured tool invocation:

**Tool Definition (LangChain-inspired decorator):**
```python
from .tool_schema import tool

@tool
def read_file(path: str) -> str:
    """Read contents of a file.

    Args:
        path: Path to file to read
    """
    return Path(path).read_text()
```

The `@tool` decorator:
- Extracts schema from function signature and docstring
- Converts Python types to JSON schema types
- Creates ToolSchema object with OpenRouter-compatible format
- Skips internal parameters (those starting with `_`)

**Tool Execution Loop (runtime.py:206-299):**
1. Build messages array with system prompt + history
2. Build tools array from agent's capabilities
3. Call LLM with messages + tools
4. If model returns tool_calls:
   - Execute each tool function
   - Add results to messages as "tool" role
   - Loop back to step 3
5. Return final text response when no more tool calls

**Benefits over string-based approach:**
- Structured, reliable tool calls (no parsing needed)
- Automatic parameter validation via JSON schema
- Models trained specifically for function calling format
- Built-in execution loop with tool results

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

### 5. Web Interface Architecture

The web interface uses async/await for non-blocking streaming:

**Key Differences from CLI:**
- `AgentSession` (async) vs `AgentRuntime` (sync)
- `StreamingModel` (async SSE parsing) vs `OpenRouterLanguageModel` (sync)
- WebSocket streaming vs console I/O
- Tools run in thread pool (asyncio.to_thread) to avoid blocking

**Streaming Flow:**
```python
# In AgentSession.handle_user_message()
async for chunk in self.model.chat_stream(messages, tools):
    if chunk["type"] == "content":
        await websocket.send_json({"type": "stream_chunk", "content": chunk["delta"]})
    elif chunk["type"] == "tool_calls":
        # Execute tool (in thread pool if sync)
        result = await asyncio.to_thread(tool_func, **args)
        await websocket.send_json({"type": "tool_result", "result": result})
```

**WebSocket Protocol:**
- Client sends: `{"type": "message", "content": "user message"}`
- Server streams: `{"type": "stream_chunk", "content": "..."}`
- Tool calls: `{"type": "tool_call", "tool": "read_file", "args": {...}}`
- Tool results: `{"type": "tool_result", "result": "..."}`
- Complete: `{"type": "stream_complete"}`

**SSE Parsing:**
The StreamingModel parses Server-Sent Events from OpenRouter:
```
data: {"choices": [{"delta": {"content": "Hello"}}]}
data: {"choices": [{"delta": {"tool_calls": [...]}}]}
data: [DONE]
```

Each `data:` line is parsed as JSON and yielded as a chunk.

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

**tool_schema.py**
- `@tool` decorator extracts schema from functions
- `ToolSchema` dataclass with to_openrouter_format() method
- Converts Python types to JSON schema types
- Parses docstrings for parameter descriptions

**tools.py**
- Tool functions decorated with @tool
- Each function takes `_manager` param for testability (auto-injected by runtime)
- Functions return strings (success/error messages)
- `TOOL_SCHEMAS` registry maps names to ToolSchema objects
- `TOOL_REGISTRY` for backward compatibility (maps to functions)

**runtime.py**
- `AgentRuntime` class runs the function calling loop
- Loads tool schemas based on capabilities
- Uses OpenRouter function calling API with tools parameter
- Executes tool calls and returns results to LLM
- Handles special commands (/help, /capabilities, /tools, /clear)
- Saves/loads history

**cli.py**
- Argument parsing
- Agent selection logic
- Management commands (list, import, export, delete)
- Bootstrap triggering
- Runtime instantiation

**web/server.py**
- FastAPI application setup
- REST API endpoints: GET /api/agents, GET /api/agents/{name}
- WebSocket endpoint: /ws/chat/{agent_name}
- Serves static React frontend from web/static/
- CORS middleware for development
- Main entry point via `main()` function

**web/agent_session.py**
- `AgentSession` class - async equivalent of AgentRuntime
- Manages streaming chat with async/await
- Executes synchronous tools in thread pool (asyncio.to_thread)
- Handles tool execution loop (max 10 iterations)
- Saves/loads history on connect/disconnect
- Uses StreamingModel for OpenRouter SSE streaming

**web/streaming_model.py**
- `StreamingModel` class - async OpenRouter client with SSE parsing
- Parses Server-Sent Events from OpenRouter API
- Yields chunks: content (text), tool_calls (function calls), usage (token stats)
- Accumulates partial tool calls across chunks
- 60-second timeout for OpenRouter requests
- Comprehensive error handling for streaming failures

**web/messages.py**
- WebSocket protocol message type definitions
- Message types: message, stream_chunk, tool_call, tool_result, stream_complete, info, error
- Type hints for client/server communication

**web/static/**
- Built React frontend (from web-ui/dist/)
- Served by FastAPI StaticFiles at root URL
- index.html entry point

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
2. Implement tool functions in `tools.py` (decorated with @tool)
3. Add tool names to `TOOL_SCHEMAS` registry
4. Test with an agent that has the capability

### Adding a New Tool

1. Implement function in `tools.py` with proper type hints and docstring:
   ```python
   @tool
   def my_tool(param1: str, param2: int = 10, _manager=None) -> str:
       """Brief description of what the tool does.

       Args:
           param1: Description of param1
           param2: Description of param2
           _manager: Internal parameter (auto-injected, not in schema)
       """
       return f"Result: {param1} x {param2}"
   ```
2. Add to `TOOL_SCHEMAS` dictionary
3. Add tool name to appropriate capability in `capabilities.py`
4. Write tests in `tests/test_tools.py`

**Important:** The @tool decorator automatically extracts the schema, so ensure:
- All parameters have type hints
- Docstring includes Args section with parameter descriptions
- Internal params (like `_manager`) start with underscore

### Modifying Agent Structure

1. Update `Agent` dataclass in `agent.py`
2. Update `to_dict()` and `from_dict()` methods
3. Update tests in `tests/test_agent.py`
4. Migration: existing agents will use defaults for new fields

### Working with the Web Interface

**Running the web server:**
```bash
source venv/bin/activate
python -m aba.web.server
# Access at http://localhost:8000
```

**Building the React frontend:**
```bash
cd web-ui
npm install
npm run build  # Output to ../src/aba/web/static/
```

**Adding a new WebSocket message type:**
1. Define message structure in `web/messages.py`
2. Handle in `AgentSession.handle_user_message()` (server)
3. Send/receive in `useWebSocket.ts` hook (client)
4. Update `ChatMessage.tsx` if displaying new message type

**Debugging WebSocket issues:**
- Check browser console for `[WebSocket]` logs
- Check server logs for connection/message events
- See `TROUBLESHOOTING.md` for common issues

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

**Web interface issues:**
```bash
# Check if server is running
lsof -i :8000

# View server logs (if running in background)
# Check browser console for client-side logs

# Rebuild frontend
cd web-ui && npm run build

# See TROUBLESHOOTING.md for detailed web interface debugging
```

## Implementation Notes

**CLI Runtime:**
- Agents are immutable during runtime (config changes don't persist unless saved)
- History is saved on runtime exit, not continuously
- Last-used agent is set on normal exit only (not on Ctrl+C)
- Tool execution is synchronous (no async/await)
- Function calling uses OpenRouter's native API (not custom parsing)
- Tool execution loop has 10 iteration limit to prevent infinite loops
- Messages include last 20 messages (10 exchanges) to avoid context overflow
- Tool schemas auto-generated from type hints and docstrings via @tool decorator
- Internal parameters (starting with _) excluded from schemas but auto-injected at runtime

**Web Interface:**
- Web interface uses async/await throughout (AgentSession, StreamingModel)
- Synchronous tools run in thread pool via asyncio.to_thread
- History saved on WebSocket disconnect (not continuously during conversation)
- OpenRouter SSE streaming parsed manually (Server-Sent Events format)
- WebSocket sends real-time chunks as they arrive from OpenRouter
- Tool execution visible to client with tool_call and tool_result messages
- 60-second timeout for OpenRouter API requests
- CORS enabled for development (Vite dev server on port 5173)
- Built frontend served from web/static/ by FastAPI
- Context tracking via get_context_info tool (added for web UI)
