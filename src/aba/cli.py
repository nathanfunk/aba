"""Command line interface for the Agent Building Agent."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .agent_builder import AgentBuilderAgent
from .language_model import RuleBasedLanguageModel


def _load_specification(args: argparse.Namespace) -> str:
    if args.file:
        path = Path(args.file)
        if not path.exists():
            raise SystemExit(f"Specification file not found: {path}")
        return path.read_text()
    if args.specification:
        return args.specification
    return sys.stdin.read()


def _print_plan(plan) -> None:
    print(f"Agent name: {plan.name}")
    print(f"Summary: {plan.summary}")
    print("\nCapabilities:")
    for capability in plan.capabilities:
        print(
            f" - {capability.name} ({capability.priority}): {capability.description}\n   Rationale: {capability.rationale}"
        )
    print("\nRecommended tools:")
    for tool in plan.recommended_tools:
        print(f" - {tool}")
    if plan.memory_strategy:
        print(f"\nMemory strategy: {plan.memory_strategy}")
    else:
        print("\nMemory strategy: to be defined")
    print("\nConversation starters:")
    for line in plan.conversation_starters:
        print(f" - {line}")


def app(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Agent Building Agent CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser("plan", help="Generate a plan from a specification")
    plan_parser.add_argument("specification", nargs="?", help="Inline specification text")
    plan_parser.add_argument("--file", help="Path to a specification file")

    materialize_parser = subparsers.add_parser(
        "materialize", help="Generate files for the target agent"
    )
    materialize_parser.add_argument("specification", nargs="?", help="Inline specification text")
    materialize_parser.add_argument("--file", help="Path to a specification file")
    materialize_parser.add_argument(
        "--output", default="generated_agents", help="Directory to write agent files"
    )

    args = parser.parse_args(argv)

    model = RuleBasedLanguageModel()
    agent = AgentBuilderAgent(language_model=model)
    specification = _load_specification(args)
    plan = agent.plan(specification)

    if args.command == "plan":
        _print_plan(plan)
    elif args.command == "materialize":
        plan = agent.materialize(specification, args.output)
        _print_plan(plan)
        print(f"\nArtifacts written to: {args.output}")
    else:  # pragma: no cover - guarded by argparse
        parser.error("Unknown command")


if __name__ == "__main__":  # pragma: no cover
    app()
