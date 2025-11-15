# Repository Guidelines

## Project Structure & Module Organization
The codebase follows a simple Python package layout. Core logic lives under `src/aba/`: `agent_builder.py` orchestrates planning and materialization, `planning.py` defines `AgentPlan`/`CapabilitySuggestion`, `language_model.py` hosts the rule-based LLM stub, and `cli.py` wires everything into the `aba` executable. Tests reside in `tests/` (e.g., `tests/test_agent_builder.py`) and assume `src` on the Python path via `pyproject.toml`. Generated artifacts land under `generated_agents/` or a user-specified directory; never commit those outputs unless they are part of a fixture.

## Build, Test, and Development Commands
- `pip install -e .` – install the CLI in editable mode; append `.[dev]` for pytest.
- `aba plan --file spec.txt` – print the structured plan inferred from a brief.
- `aba materialize --file spec.txt --output agents/demo` – emit runtime scaffolding and recap the plan.
- `aba chat --file spec.txt` – launch a REPL that answers questions using the inferred plan; type `exit` to quit.
- `pytest` – run the entire suite (configured via `pyproject.toml` to auto-discover under `tests/`).
Use `python -m aba.cli plan "Build a travel agent"` when iterating without reinstalling.

## Coding Style & Naming Conventions
Target Python 3.10+ and keep code PEP 8 compliant (4-space indents, 88–100 char lines). Public functions, dataclasses, and CLI entry points are type-annotated; match that convention and prefer `from __future__ import annotations` for new modules. Module names stay lowercase with underscores, classes use PascalCase (`AgentBuilderAgent`), and test helpers/functions follow `snake_case`. Maintain deterministic, offline-safe behavior—avoid network calls or randomness unless gated by explicit flags.

## Testing Guidelines
Pytest is the only test runner. Place new tests in `tests/test_<feature>.py`, mirror the module under test, and give test functions descriptive names like `test_plan_infers_capabilities`. Use simple fixtures or inline specs to keep cases self-contained; mock filesystem writes by targeting `tmp_path` when exercising `materialize`. Aim for high coverage on heuristics paths (plan inference, CLI argument parsing) and include regression tests whenever modifying inference rules or file layouts.

## Commit & Pull Request Guidelines
Existing commits use short, imperative summaries (e.g., “Add agent building agent core package”). Follow that style, keep the first line under ~60 characters, and add a concise body when rationale or context is non-obvious. Pull requests should link issues when available, describe user-facing changes, and list validation evidence (command outputs, pytest runs, or sample `aba plan` transcripts). Include screenshots only if CLI output formatting changes. Ensure PRs leave the working tree clean and omit generated agent folders.

## Security & Configuration Tips
ABA is designed to run offline; do not add dependencies on remote APIs or credentials. Keep sample specifications free of sensitive data, and default new options to the safest behavior possible (e.g., writing under `generated_agents/` rather than system paths).
