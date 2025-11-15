"""Command line interface for Agent Builder."""

from __future__ import annotations

import argparse
import json
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
        try:
            agent = manager.load_agent(name)
            caps = f"[{', '.join(agent.capabilities)}]" if agent.capabilities else "[chat only]"
            print(f"{prefix} {name} - {agent.description} {caps}")
        except Exception:
            print(f"{prefix} {name}")


def _import_agent(manager: AgentManager, import_file: str) -> None:
    """Import an agent from JSON file."""
    from .agent import Agent

    try:
        with open(import_file) as f:
            data = json.load(f)

        agent = Agent.from_dict(data)
        manager.save_agent(agent)
        print(f"✓ Imported agent '{agent.name}'")
    except FileNotFoundError:
        print(f"Error: File '{import_file}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error importing agent: {e}")
        sys.exit(1)


def _export_agent(manager: AgentManager, agent_name: str, output_file: str = None) -> None:
    """Export an agent to JSON file."""
    try:
        agent = manager.load_agent(agent_name)

        if output_file is None:
            output_file = f"{agent_name}.json"

        with open(output_file, 'w') as f:
            json.dump(agent.to_dict(), f, indent=2)

        print(f"✓ Exported agent '{agent_name}' to {output_file}")
    except FileNotFoundError:
        print(f"Error: Agent '{agent_name}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error exporting agent: {e}")
        sys.exit(1)


def app(argv: list[str] | None = None) -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Agent Builder - Run and manage AI agents",
        epilog="Examples:\n"
               "  aba                    # Run last used agent\n"
               "  aba agent-builder      # Run specific agent\n"
               "  aba --list             # List all agents\n"
               "  aba --model gpt-4      # Override model for this session",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

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
        _export_agent(manager, args.export)
        return

    if args.delete:
        confirm = input(f"Delete agent '{args.delete}'? (y/N): ")
        if confirm.lower() == 'y':
            try:
                manager.delete_agent(args.delete)
                print(f"✓ Deleted agent '{args.delete}'")
            except Exception as e:
                print(f"Error: {e}")
                sys.exit(1)
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
        print(f"✓ Created '{agent.name}'")
        print(f"  Description: {agent.description}")
        print(f"  Capabilities: {', '.join(agent.capabilities)}\n")
    else:
        if agent_name is None:
            # No agent specified and no last agent - default to agent-builder
            if manager.agent_exists("agent-builder"):
                agent_name = "agent-builder"
            else:
                # Use first available agent
                agent_name = agents[0]

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
    try:
        runtime = AgentRuntime(agent, manager)
        runtime.run()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    app()
