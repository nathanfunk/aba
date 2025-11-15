# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Agent Building Agent (ABA) is a lightweight toolkit that transforms agent ideas into concrete scaffolds. It operates offline by default using rule-based reasoning to analyze specifications, propose capabilities, and generate starter files.

## Key Commands

**Installation:**
```bash
pip install -e .        # Editable install for development
pip install -e .[dev]   # Include pytest for testing
```

**Core CLI Commands:**
```bash
aba                                                   # Interactive chat (default, requires OPENROUTER_API_KEY)
aba --model "openai/gpt-3.5-turbo"                   # Chat with specific model
aba plan --file spec.txt                              # Generate structured plan from specification
aba materialize --file spec.txt --output ./my_agent   # Generate Python scaffold files
```

**Development:**
```bash
pytest                                    # Run all tests
pytest tests/test_agent_builder.py       # Run specific test file
pytest -v                                 # Verbose test output
python -m aba.cli plan "Build a travel agent"  # Test without reinstalling
```

## Architecture

**Core Flow:**
1. `cli.py` (entry point) → parses commands and loads specifications
2. `AgentBuilderAgent` (agent_builder.py) → orchestrates planning and file generation
3. `planning.py` → defines data structures (AgentPlan, CapabilitySuggestion, FileArtifact)
4. `language_model.py` → provides RuleBasedLanguageModel (offline) and OpenRouterLanguageModel (online)
5. Generated artifacts land in `generated_agents/` or user-specified output directory

**Planning Pipeline:**
- `plan()` method in AgentBuilderAgent performs inference via heuristics:
  - `_infer_name()` - extracts agent name from specification
  - `_infer_capabilities()` - keyword matching against predefined capability map (research, code, test, plan, data, etc.)
  - `_infer_tools()` - suggests tools based on detected capabilities
  - `_infer_memory()` - recommends memory strategy
  - `_conversation_starters()` - generates greeting prompts
- `generate_file_artifacts()` - produces Python runtime module and README
- `materialize()` - writes artifacts to disk

**Language Model Abstraction:**
- `LanguageModel` protocol defines `complete(prompt: str) -> str`
- `RuleBasedLanguageModel` - deterministic, offline, pattern-matching responses
- `OpenRouterLanguageModel` - HTTP-based completion via OpenRouter API

**Chat Mode:**
- Lives in `cli.py:_run_chat_interface()` and `chat.py:AgentChatSession`
- Interactive REPL that uses `AgentPlan` to ground responses
- Type `/exit` or `/quit` to leave chat loop

## Important Patterns

**Offline-First Design:**
- Default behavior must work without network access
- `RuleBasedLanguageModel` ensures deterministic, testable output
- Only `chat` command requires external API (OpenRouter)

**Heuristic-Based Inference:**
- Keyword detection drives capability inference (see `_infer_capabilities()` in agent_builder.py:177)
- Priority cycling: first detected capability gets "high", second gets "medium", third gets "low", repeat
- Fallback to "General Assistance" if no keywords match

**File Generation:**
- Agent class name derived from slugified plan name (e.g., "Travel Agent" → "TravelAgent")
- Output structure: `{output_dir}/agents/{slug}/core.py` and `README.md`
- Generated Python includes Task dataclass and agent runtime skeleton

## Testing Conventions

- Test files mirror source structure: `tests/test_agent_builder.py` tests `src/aba/agent_builder.py`
- Use pytest fixtures for file I/O (e.g., `tmp_path` for materialize tests)
- Tests assume `pythonpath = ["src"]` from pyproject.toml
- Maintain deterministic test behavior - avoid randomness or network calls

## Module Responsibilities

- `cli.py` - Argument parsing, command routing, chat REPL loop
- `agent_builder.py` - Core orchestration logic for planning and materialization
- `planning.py` - Data structures only (AgentPlan, CapabilitySuggestion, FileArtifact)
- `language_model.py` - LLM abstraction and implementations
- `chat.py` - Chat session management for generated agents (separate from CLI chat)

## Configuration

- Python 3.10+ required
- Dependencies: `requests>=2.31.0` (runtime), `pytest>=7` (dev)
- No config files - all behavior controlled via CLI flags
- Environment variable: `OPENROUTER_API_KEY` for chat mode (defaults to this var name, overridable with `--api-key-env`)
