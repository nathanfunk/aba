# aba

Agent Building Agent (ABA) is a lightweight toolkit that helps you transform an
idea for a new AI agent into a concrete scaffold. It works entirely offline by
default, using rule-based reasoning to analyse a specification, propose
capabilities, and generate starter files for your project.

## Features

- Convert free-form briefs into structured agent plans.
- Suggest tools, memory strategies, and conversation starters.
- Materialise Python package scaffolds for new agents.
- Simple CLI with `plan` and `materialize` commands.

## Installation

```bash
pip install -e .
```

## Usage

Create a text file describing the agent you want to build, then run:

```bash
aba plan --file spec.txt
```

To generate files:

```bash
aba materialize --file spec.txt --output ./my_agent
```

The CLI also accepts inline specifications or reads from standard input if no
arguments are provided. Generated artifacts include a Python runtime module and
a README with the inferred plan.

## Development

Install development dependencies and run the test suite:

```bash
pip install -e .[dev]
pytest
```

## License

MIT
