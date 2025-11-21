"""End-to-end integration tests for the full system."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import json

from aba.agent_manager import AgentManager
from aba.agent import Agent
from aba.runtime import AgentRuntime
from aba.tools import create_agent, list_agents
from aba.cli import app


def test_full_bootstrap_and_agent_creation_workflow(tmp_path):
    """Test the complete workflow: bootstrap → create agent → use agent."""
    manager = AgentManager(base_path=tmp_path)

    # Step 1: Bootstrap should create agent-builder
    assert len(manager.list_agents()) == 0

    agent_builder = manager.bootstrap()

    assert agent_builder.name == "agent-builder"
    assert "agent-creation" in agent_builder.capabilities
    assert manager.agent_exists("agent-builder")
    assert manager.get_last_agent() == "agent-builder"

    # Step 2: Create a new agent using the create_agent tool
    result = create_agent(
        name="test-bot",
        description="A test chatbot",
        capabilities=[],
        system_prompt="You are a friendly test bot.",
        _manager=manager
    )

    assert "✓ Created agent 'test-bot'" in result
    assert manager.agent_exists("test-bot")

    # Step 3: Load the new agent and verify its properties
    test_bot = manager.load_agent("test-bot")

    assert test_bot.name == "test-bot"
    assert test_bot.description == "A test chatbot"
    assert test_bot.capabilities == []
    assert "friendly test bot" in test_bot.system_prompt

    # Step 4: Create a runtime for the new agent
    runtime = AgentRuntime(test_bot, manager)

    assert runtime.agent == test_bot
    assert len(runtime.tool_schemas) == 0  # No capabilities = no tools
    assert len(runtime.history) == 0

    # Step 5: Verify agent list shows both agents
    agents = manager.list_agents()
    assert "agent-builder" in agents
    assert "test-bot" in agents


def test_agent_with_file_operations_capability(tmp_path):
    """Test creating and using an agent with file-operations capability."""
    manager = AgentManager(base_path=tmp_path)

    # Create agent with file-operations
    create_agent(
        name="file-agent",
        description="File management agent",
        capabilities=["file-operations"],
        _manager=manager
    )

    # Load the agent
    file_agent = manager.load_agent("file-agent")
    runtime = AgentRuntime(file_agent, manager)

    # Verify file operation tools are available
    assert "read_file" in runtime.tool_schemas
    assert "write_file" in runtime.tool_schemas
    assert "list_files" in runtime.tool_schemas
    assert "delete_file" in runtime.tool_schemas

    # Verify system prompt includes file operations guidance
    sys_prompt = runtime._build_system_prompt()
    assert "file" in sys_prompt.lower()


def test_history_persistence_workflow(tmp_path):
    """Test that chat history persists across sessions."""
    manager = AgentManager(base_path=tmp_path)

    # Create an agent
    agent = Agent(
        name="history-test",
        description="Test history",
        config={"preserve_history": True}
    )
    manager.save_agent(agent)

    # Session 1: Create runtime and add history
    runtime1 = AgentRuntime(agent, manager)
    runtime1.history.append(("user", "Hello"))
    runtime1.history.append(("agent", "Hi there!"))
    runtime1._save_history()

    # Session 2: Create new runtime, history should be loaded
    agent2 = manager.load_agent("history-test")
    runtime2 = AgentRuntime(agent2, manager)

    assert len(runtime2.history) == 2
    assert runtime2.history[0] == ("user", "Hello")
    assert runtime2.history[1] == ("agent", "Hi there!")


def test_export_import_workflow(tmp_path):
    """Test exporting and importing an agent."""
    manager = AgentManager(base_path=tmp_path)

    # Create an agent
    original = Agent(
        name="export-test",
        description="Test export/import",
        capabilities=["file-operations", "web-access"],
        system_prompt="Custom prompt"
    )
    manager.save_agent(original)

    # Export to JSON
    export_file = tmp_path / "exported.json"
    with open(export_file, 'w') as f:
        json.dump(original.to_dict(), f, indent=2)

    # Create a new manager in a different location
    manager2 = AgentManager(base_path=tmp_path / "new")

    # Import the agent
    with open(export_file) as f:
        data = json.load(f)

    imported = Agent.from_dict(data)
    manager2.save_agent(imported)

    # Verify the imported agent matches
    assert manager2.agent_exists("export-test")
    loaded = manager2.load_agent("export-test")

    assert loaded.name == original.name
    assert loaded.description == original.description
    assert loaded.capabilities == original.capabilities
    assert loaded.system_prompt == original.system_prompt


def test_cli_end_to_end_bootstrap(tmp_path, monkeypatch, capsys):
    """Test full CLI workflow from first run."""
    manager = AgentManager(base_path=tmp_path)

    # Simulate first run - no agents exist
    inputs = iter(["/exit"])
    monkeypatch.setattr('builtins.input', lambda _: next(inputs))

    with patch('aba.cli.AgentManager') as mock_manager_class:
        mock_manager_class.return_value = manager

        with patch('aba.cli.AgentRuntime') as mock_runtime_class:
            mock_runtime = MagicMock()
            mock_runtime_class.return_value = mock_runtime

            # Run CLI with no arguments (first time)
            app([])

    # Verify bootstrap happened
    captured = capsys.readouterr()
    assert "Creating default 'agent-builder'" in captured.out
    assert manager.agent_exists("agent-builder")

    # Verify agent-builder has correct capabilities
    ab = manager.load_agent("agent-builder")
    assert "agent-creation" in ab.capabilities
    assert "file-operations" in ab.capabilities
    assert "code-execution" in ab.capabilities


def test_multiple_agents_last_used_tracking(tmp_path):
    """Test that last-used agent is tracked correctly."""
    manager = AgentManager(base_path=tmp_path)

    # Create multiple agents
    agent1 = Agent(name="agent-1", description="First")
    agent2 = Agent(name="agent-2", description="Second")
    agent3 = Agent(name="agent-3", description="Third")

    manager.save_agent(agent1)
    manager.save_agent(agent2)
    manager.save_agent(agent3)

    # Initially no last agent
    assert manager.get_last_agent() is None

    # Set last agent
    manager.set_last_agent("agent-2")
    assert manager.get_last_agent() == "agent-2"

    # Change last agent
    manager.set_last_agent("agent-3")
    assert manager.get_last_agent() == "agent-3"

    # Verify persistence across manager instances
    manager2 = AgentManager(base_path=tmp_path)
    assert manager2.get_last_agent() == "agent-3"


def test_capability_security_model(tmp_path):
    """Test that agents only get tools for their capabilities."""
    manager = AgentManager(base_path=tmp_path)

    # Minimal agent (no capabilities)
    minimal = Agent(name="minimal", description="Minimal", capabilities=[])
    manager.save_agent(minimal)
    runtime_minimal = AgentRuntime(minimal, manager)

    assert len(runtime_minimal.tool_schemas) == 0

    # Agent with one capability
    file_agent = Agent(
        name="file-only",
        description="File only",
        capabilities=["file-operations"]
    )
    manager.save_agent(file_agent)
    runtime_file = AgentRuntime(file_agent, manager)

    # Should only have file tools, not agent-creation tools
    assert "read_file" in runtime_file.tool_schemas
    assert "write_file" in runtime_file.tool_schemas
    assert "create_agent" not in runtime_file.tool_schemas
    assert "exec_python" not in runtime_file.tool_schemas

    # Agent with multiple capabilities
    power_agent = Agent(
        name="power-user",
        description="Multiple caps",
        capabilities=["file-operations", "code-execution", "agent-creation"]
    )
    manager.save_agent(power_agent)
    runtime_power = AgentRuntime(power_agent, manager)

    # Should have all tools
    assert "read_file" in runtime_power.tool_schemas
    assert "exec_python" in runtime_power.tool_schemas
    assert "create_agent" in runtime_power.tool_schemas
