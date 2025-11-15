"""Command line interface for the Agent Building Agent."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import sys
from pathlib import Path
from typing import Iterable

from .agent_builder import AgentBuilderAgent
from .language_model import OpenRouterLanguageModel, RuleBasedLanguageModel


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

def _format_chat_prompt(history: Iterable[tuple[str, str]]) -> str:
    """Format conversation history for the language model."""

    prologue = (
        "You are the Agent Building Agent, an assistant that helps people "
        "design and refine software agents. Respond with concrete advice, "
        "clarifying questions, or implementation steps based on the most "
        "recent user message."
    )
    transcript = "\n".join(f"{role.capitalize()}: {message}" for role, message in history)
    return f"{prologue}\n\n{transcript}\nAgent:"


@dataclass
class _ChatState:
    history: list[tuple[str, str]]


def _run_chat_interface(args: argparse.Namespace) -> None:
    try:
        model = OpenRouterLanguageModel(model=args.model, api_key_env=args.api_key_env)
    except RuntimeError as exc:  # pragma: no cover - requires environment configuration
        raise SystemExit(str(exc)) from exc

    state = _ChatState(history=[])
    print("Starting interactive chat with the Agent Building Agent. Type '/exit' to quit.\n")

    while True:
        try:
            user_message = input("You: ").strip()
        except EOFError:
            print()
            break

        if not user_message:
            continue

        if user_message.lower() in {"/exit", "/quit", "exit", "quit"}:
            print("Exiting chat.")
            break

        state.history.append(("user", user_message))
        prompt = _format_chat_prompt(state.history)

        try:
            response = model.complete(prompt)
        except Exception as exc:  # pragma: no cover - network error paths
            print(f"Error contacting language model: {exc}")
            state.history.pop()
            continue

        state.history.append(("agent", response))
        print(f"Agent: {response}\n")


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

    chat_parser = subparsers.add_parser("chat", help="Start an interactive planning chat")
    chat_parser.add_argument(
        "--model",
        default="openai/gpt-4o-mini",
        help="OpenRouter model identifier to use for responses",
    )
    chat_parser.add_argument(
        "--api-key-env",
        default="OPENROUTER_API_KEY",
        help="Environment variable containing the OpenRouter API key",
    )

    args = parser.parse_args(argv)

    if args.command == "chat":
        _run_chat_interface(args)
        return

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
