"""Tests for the AgentRuntime."""

from unittest.mock import MagicMock, patch

from aba.agent import Agent
from aba.agent_manager import AgentManager
from aba.runtime import AgentRuntime


def test_runtime_initialization(tmp_path):
    """Test that AgentRuntime initializes correctly."""
    manager = AgentManager(base_path=tmp_path)
    agent = Agent(
        name="test-agent",
        description="Test agent",
        capabilities=["file-operations"]
    )

    runtime = AgentRuntime(agent, manager)

    assert runtime.agent == agent
    assert runtime.manager == manager
    assert len(runtime.tool_schemas) > 0  # Should have file operation tools
    assert runtime.history == []


def test_runtime_loads_tools_for_capabilities(tmp_path):
    """Test that runtime loads correct tools based on capabilities."""
    manager = AgentManager(base_path=tmp_path)

    # Agent with file-operations capability
    agent = Agent(
        name="file-agent",
        description="File agent",
        capabilities=["file-operations"]
    )
    runtime = AgentRuntime(agent, manager)

    assert "read_file" in runtime.tool_schemas
    assert "write_file" in runtime.tool_schemas
    assert "list_files" in runtime.tool_schemas

    # Agent with no capabilities
    minimal_agent = Agent(
        name="minimal",
        description="Minimal agent",
        capabilities=[]
    )
    minimal_runtime = AgentRuntime(minimal_agent, manager)

    assert len(minimal_runtime.tool_schemas) == 0


def test_runtime_builds_system_prompt(tmp_path):
    """Test that runtime builds system prompt with capability additions."""
    manager = AgentManager(base_path=tmp_path)

    agent = Agent(
        name="test-agent",
        description="Test",
        capabilities=["file-operations"],
        system_prompt="You are a helpful assistant."
    )

    runtime = AgentRuntime(agent, manager)
    prompt = runtime._build_system_prompt()

    assert "You are a helpful assistant." in prompt
    assert "file" in prompt.lower()  # Capability addition


def test_runtime_loads_history(tmp_path):
    """Test that runtime loads saved history."""
    manager = AgentManager(base_path=tmp_path)

    agent = Agent(name="test-agent", description="Test")
    manager.save_agent(agent)

    # Save some history
    history_file = manager.history_dir / "test-agent.json"
    import json
    history_data = [
        {"role": "user", "message": "Hello"},
        {"role": "agent", "message": "Hi there!"}
    ]
    with open(history_file, 'w') as f:
        json.dump(history_data, f)

    # Load runtime
    runtime = AgentRuntime(agent, manager)

    assert len(runtime.history) == 2
    assert runtime.history[0] == ("user", "Hello")
    assert runtime.history[1] == ("agent", "Hi there!")


def test_runtime_saves_history(tmp_path):
    """Test that runtime saves history on exit."""
    manager = AgentManager(base_path=tmp_path)

    agent = Agent(name="test-agent", description="Test")
    runtime = AgentRuntime(agent, manager)

    # Add some history
    runtime.history.append(("user", "Test message"))
    runtime.history.append(("agent", "Test response"))

    # Save history
    runtime._save_history()

    # Verify file was created
    history_file = manager.history_dir / "test-agent.json"
    assert history_file.exists()

    # Verify content
    import json
    with open(history_file) as f:
        data = json.load(f)

    assert len(data) == 2
    assert data[0]["role"] == "user"
    assert data[0]["message"] == "Test message"


def test_runtime_respects_no_history_config(tmp_path):
    """Test that runtime doesn't save history when preserve_history is False."""
    manager = AgentManager(base_path=tmp_path)

    agent = Agent(
        name="test-agent",
        description="Test",
        config={"preserve_history": False}
    )

    runtime = AgentRuntime(agent, manager)
    runtime.history.append(("user", "Test"))
    runtime._save_history()

    # History should not be saved
    history_file = manager.history_dir / "test-agent.json"
    assert not history_file.exists()


def test_runtime_chat_with_mocked_input(tmp_path, monkeypatch, capsys):
    """Test runtime chat loop with mocked user input."""
    manager = AgentManager(base_path=tmp_path)
    agent = Agent(name="test-agent", description="Test agent")

    inputs = iter(["/exit"])
    monkeypatch.setattr('builtins.input', lambda _: next(inputs))

    with patch('aba.runtime.OpenRouterLanguageModel') as mock_model_class:
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        runtime = AgentRuntime(agent, manager)
        runtime.run()

    captured = capsys.readouterr()
    assert "Starting chat with 'test-agent'" in captured.out
    assert "Exiting chat" in captured.out


def test_runtime_handles_help_command(tmp_path, monkeypatch, capsys):
    """Test that /help command shows help text."""
    manager = AgentManager(base_path=tmp_path)
    agent = Agent(name="test-agent", description="Test")

    inputs = iter(["/help", "/exit"])
    monkeypatch.setattr('builtins.input', lambda _: next(inputs))

    with patch('aba.runtime.OpenRouterLanguageModel') as mock_model_class:
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        runtime = AgentRuntime(agent, manager)
        runtime.run()

    captured = capsys.readouterr()
    assert "Available commands:" in captured.out
    assert "/capabilities" in captured.out


def test_runtime_handles_capabilities_command(tmp_path, monkeypatch, capsys):
    """Test that /capabilities command shows agent capabilities."""
    manager = AgentManager(base_path=tmp_path)
    agent = Agent(
        name="test-agent",
        description="Test",
        capabilities=["file-operations", "web-access"]
    )

    inputs = iter(["/capabilities", "/exit"])
    monkeypatch.setattr('builtins.input', lambda _: next(inputs))

    with patch('aba.runtime.OpenRouterLanguageModel') as mock_model_class:
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        runtime = AgentRuntime(agent, manager)
        runtime.run()

    captured = capsys.readouterr()
    assert "file-operations" in captured.out
    assert "web-access" in captured.out


def test_runtime_handles_clear_command(tmp_path, monkeypatch, capsys):
    """Test that /clear command clears history."""
    manager = AgentManager(base_path=tmp_path)
    agent = Agent(name="test-agent", description="Test")

    inputs = iter(["/clear", "/exit"])
    monkeypatch.setattr('builtins.input', lambda _: next(inputs))

    with patch('aba.runtime.OpenRouterLanguageModel') as mock_model_class:
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        runtime = AgentRuntime(agent, manager)
        runtime.history.append(("user", "Old message"))

        runtime.run()

    # History should be cleared
    assert len(runtime.history) == 0

    captured = capsys.readouterr()
    assert "History cleared" in captured.out
