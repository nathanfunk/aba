"""Tests for the new CLI."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import json

from aba.cli import _list_agents, _import_agent, _export_agent, app
from aba.agent_manager import AgentManager
from aba.agent import Agent


def test_list_agents_empty(tmp_path, capsys):
    """Test listing agents when none exist."""
    manager = AgentManager(base_path=tmp_path)

    _list_agents(manager)

    captured = capsys.readouterr()
    assert "No agents found" in captured.out


def test_list_agents_with_agents(tmp_path, capsys):
    """Test listing agents."""
    manager = AgentManager(base_path=tmp_path)

    # Create some agents
    agent1 = Agent(name="agent-one", description="First agent")
    agent2 = Agent(name="agent-two", description="Second agent", capabilities=["file-operations"])

    manager.save_agent(agent1)
    manager.save_agent(agent2)
    manager.set_last_agent("agent-one")

    _list_agents(manager)

    captured = capsys.readouterr()
    assert "agent-one" in captured.out
    assert "agent-two" in captured.out
    assert "First agent" in captured.out
    assert "[chat only]" in captured.out
    assert "[file-operations]" in captured.out
    assert "*" in captured.out  # Indicates last used agent


def test_import_agent(tmp_path, capsys):
    """Test importing an agent from JSON."""
    manager = AgentManager(base_path=tmp_path)

    # Create a JSON file
    agent_data = {
        "name": "imported-agent",
        "description": "An imported agent",
        "capabilities": ["web-access"]
    }
    json_file = tmp_path / "agent.json"
    with open(json_file, 'w') as f:
        json.dump(agent_data, f)

    _import_agent(manager, str(json_file))

    captured = capsys.readouterr()
    assert "✓ Imported agent 'imported-agent'" in captured.out
    assert manager.agent_exists("imported-agent")

    # Verify agent details
    agent = manager.load_agent("imported-agent")
    assert agent.name == "imported-agent"
    assert agent.capabilities == ["web-access"]


def test_export_agent(tmp_path, capsys):
    """Test exporting an agent to JSON."""
    manager = AgentManager(base_path=tmp_path)

    # Create an agent
    agent = Agent(
        name="export-test",
        description="Test export",
        capabilities=["file-operations"]
    )
    manager.save_agent(agent)

    # Export it
    output_file = tmp_path / "exported.json"
    _export_agent(manager, "export-test", str(output_file))

    captured = capsys.readouterr()
    assert "✓ Exported agent 'export-test'" in captured.out
    assert output_file.exists()

    # Verify exported data
    with open(output_file) as f:
        data = json.load(f)

    assert data["name"] == "export-test"
    assert data["description"] == "Test export"
    assert data["capabilities"] == ["file-operations"]


def test_cli_list_command(tmp_path, capsys):
    """Test CLI --list command."""
    manager = AgentManager(base_path=tmp_path)
    manager.bootstrap()

    with patch('aba.cli.AgentManager') as mock_manager_class:
        mock_manager_class.return_value = manager
        app(["--list"])

    captured = capsys.readouterr()
    assert "agent-builder" in captured.out


def test_cli_bootstrap_on_first_run(tmp_path, monkeypatch, capsys):
    """Test that CLI bootstraps agent-builder on first run."""
    manager = AgentManager(base_path=tmp_path)

    # Mock input to exit immediately
    inputs = iter(["/exit"])
    monkeypatch.setattr('builtins.input', lambda _: next(inputs))

    with patch('aba.cli.AgentManager') as mock_manager_class:
        mock_manager_class.return_value = manager

        with patch('aba.cli.AgentRuntime') as mock_runtime_class:
            mock_runtime = MagicMock()
            mock_runtime_class.return_value = mock_runtime

            app([])

    captured = capsys.readouterr()
    assert "Creating default 'agent-builder'" in captured.out
    assert manager.agent_exists("agent-builder")


def test_cli_run_specific_agent(tmp_path, monkeypatch):
    """Test running a specific agent by name."""
    manager = AgentManager(base_path=tmp_path)

    # Create an agent
    agent = Agent(name="test-agent", description="Test")
    manager.save_agent(agent)

    inputs = iter(["/exit"])
    monkeypatch.setattr('builtins.input', lambda _: next(inputs))

    with patch('aba.cli.AgentManager') as mock_manager_class:
        mock_manager_class.return_value = manager

        with patch('aba.cli.AgentRuntime') as mock_runtime_class:
            mock_runtime = MagicMock()
            mock_runtime_class.return_value = mock_runtime

            app(["test-agent"])

            # Verify the runtime was created with the correct agent
            mock_runtime_class.assert_called_once()
            called_agent = mock_runtime_class.call_args[0][0]
            assert called_agent.name == "test-agent"


def test_cli_model_override(tmp_path, monkeypatch):
    """Test --model flag overrides agent's default model."""
    manager = AgentManager(base_path=tmp_path)
    agent = Agent(name="test-agent", description="Test")
    manager.save_agent(agent)

    inputs = iter(["/exit"])
    monkeypatch.setattr('builtins.input', lambda _: next(inputs))

    with patch('aba.cli.AgentManager') as mock_manager_class:
        mock_manager_class.return_value = manager

        with patch('aba.cli.AgentRuntime') as mock_runtime_class:
            mock_runtime = MagicMock()
            mock_runtime_class.return_value = mock_runtime

            app(["test-agent", "--model", "custom-model"])

            # Verify agent config was updated
            called_agent = mock_runtime_class.call_args[0][0]
            assert called_agent.config["model"] == "custom-model"


def test_cli_no_history_flag(tmp_path, monkeypatch):
    """Test --no-history flag disables history."""
    manager = AgentManager(base_path=tmp_path)
    agent = Agent(name="test-agent", description="Test")
    manager.save_agent(agent)

    inputs = iter(["/exit"])
    monkeypatch.setattr('builtins.input', lambda _: next(inputs))

    with patch('aba.cli.AgentManager') as mock_manager_class:
        mock_manager_class.return_value = manager

        with patch('aba.cli.AgentRuntime') as mock_runtime_class:
            mock_runtime = MagicMock()
            mock_runtime_class.return_value = mock_runtime

            app(["test-agent", "--no-history"])

            # Verify history was disabled
            called_agent = mock_runtime_class.call_args[0][0]
            assert called_agent.config["preserve_history"] is False
