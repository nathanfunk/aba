# Agent Builder (aba)

A lightweight framework for creating and running AI agents with capability-based permissions.

## Overview

Agent Builder is a multi-agent system where each agent is self-contained and capability-based. Agents are minimal by default (chat only) and can be granted specific capabilities like file operations, code execution, web access, or the ability to create other agents.

The system includes a special `agent-builder` agent that can create and manage other agents.

## Features

- **Multi-agent management** - Create and run multiple specialized agents
- **Capability-based security** - Agents only get the permissions they need
- **Persistent chat history** - Conversations resume where you left off
- **Self-bootstrapping** - Creates the agent-builder on first run
- **Simple CLI** - Just type `aba` to start chatting

## Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install in development mode
pip install -e .
```

## Quick Start

```bash
# First run - auto-creates agent-builder
aba

# The agent-builder can create other agents
[agent-builder] You: Create a code review agent with file-operations capability
[agent-builder] Agent: I'll create that agent for you...

# List all agents
aba --list

# Run a specific agent
aba code-reviewer

# Get help
aba --help
```

## Usage

### Running Agents

```bash
# Run last used agent
aba

# Run specific agent by name
aba agent-builder
aba my-research-bot

# Override model for this session
aba --model "openai/gpt-3.5-turbo"

# Disable history for this session
aba --no-history
```

### Managing Agents

```bash
# List all agents
aba --list

# Export an agent to JSON
aba --export agent-builder

# Import an agent from JSON
aba --import agent.json

# Delete an agent
aba --delete old-agent
```

### In-Chat Commands

While chatting with an agent:

```
/help         - Show available commands
/capabilities - Show agent's capabilities
/tools        - Show available tools
/clear        - Clear conversation history
/exit, /quit  - Exit chat
```

## Architecture

### Agent Storage

Agents are stored as JSON files in `~/.aba/`:

```
~/.aba/
├── config.json              # Last used agent
├── agents/
│   ├── agent-builder.json   # Meta-agent that creates other agents
│   ├── code-reviewer.json
│   └── research-bot.json
└── history/
    ├── agent-builder.json   # Chat history
    ├── code-reviewer.json
    └── research-bot.json
```

### Agent Structure

Each agent is defined by:

```json
{
  "name": "code-reviewer",
  "description": "Reviews code and suggests improvements",
  "capabilities": ["file-operations"],
  "system_prompt": "You are an expert code reviewer...",
  "config": {
    "model": "openai/gpt-4o-mini",
    "preserve_history": true
  }
}
```

### Available Capabilities

- **agent-creation** - Create and modify other agents
- **file-operations** - Read, write, list, and delete files
- **code-execution** - Execute Python code and shell commands
- **web-access** - Search the web and fetch URLs (placeholder)

Most agents should have **no capabilities** and just use the language model for conversation.

## Creating Custom Agents

### Using agent-builder (Recommended)

```bash
aba agent-builder

[agent-builder] You: Create a research assistant with web-access
[agent-builder] Agent: I'll create that for you...
```

### Manually

Create a JSON file and import it:

```json
{
  "name": "greeter",
  "description": "A friendly greeting bot",
  "capabilities": [],
  "system_prompt": "You are a friendly bot that greets people warmly."
}
```

```bash
aba --import greeter.json
aba greeter
```

## Development

### Install Development Dependencies

```bash
pip install -e .[dev]
```

### Run Tests

```bash
pytest                 # Run all tests
pytest -v              # Verbose output
pytest tests/test_cli.py  # Run specific test file
```

### Project Structure

```
src/aba/
├── agent.py           # Agent data model
├── agent_manager.py   # Agent CRUD operations
├── capabilities.py    # Capability definitions
├── tools.py           # Tool implementations
├── runtime.py         # Agent execution runtime
├── language_model.py  # LLM integrations
└── cli.py             # Command-line interface

tests/
├── test_agent.py
├── test_agent_manager.py
├── test_capabilities.py
├── test_tools.py
├── test_runtime.py
└── test_cli.py
```

## Configuration

### Environment Variables

- `OPENROUTER_API_KEY` - Required for chat functionality (get a free key at [OpenRouter](https://openrouter.ai/))

### Agent Config Options

Each agent can configure:

```json
{
  "config": {
    "model": "openai/gpt-4o-mini",      // OpenRouter model ID
    "temperature": 0.7,                  // Sampling temperature
    "preserve_history": true             // Save chat history
  }
}
```

## Examples

### Code Review Agent

```json
{
  "name": "code-reviewer",
  "description": "Reviews code and suggests improvements",
  "capabilities": ["file-operations"],
  "system_prompt": "You are an expert code reviewer. Analyze code for bugs, performance issues, and best practices. Provide specific, actionable feedback."
}
```

### Research Assistant

```json
{
  "name": "researcher",
  "description": "Helps with web research",
  "capabilities": ["web-access"],
  "system_prompt": "You are a research assistant. Help users find information, summarize findings, and provide well-researched answers."
}
```

### Script Generator

```json
{
  "name": "script-gen",
  "description": "Generates and tests Python scripts",
  "capabilities": ["file-operations", "code-execution"],
  "system_prompt": "You are a Python script generator. Create clean, well-documented scripts and test them before presenting to the user."
}
```

## Security

- Agents are **minimal by default** - they have no capabilities unless explicitly granted
- Code execution and file operations require explicit capability grants
- The agent-builder is the only agent created with elevated capabilities
- Always review generated agents before granting dangerous capabilities

## Troubleshooting

### "No agents found"

On first run, the system auto-creates `agent-builder`. If deleted:

```bash
aba  # Will recreate agent-builder automatically
```

### "Error contacting language model"

Ensure your OpenRouter API key is set:

```bash
export OPENROUTER_API_KEY="sk-or-v1-..."
aba
```

### Reset Everything

```bash
rm -rf ~/.aba
aba  # Starts fresh
```

## License

MIT
