"""Tests for the AgentManager."""

from pathlib import Path

from aba.agent import Agent
from aba.agent_manager import AgentManager


def test_agent_manager_initialization(tmp_path):
    """Test that AgentManager creates required directories."""
    manager = AgentManager(base_path=tmp_path)

    assert manager.agents_dir.exists()
    assert manager.history_dir.exists()
    assert manager.agents_dir == tmp_path / "agents"
    assert manager.history_dir == tmp_path / "history"


def test_save_and_load_agent(tmp_path):
    """Test saving and loading an agent."""
    manager = AgentManager(base_path=tmp_path)

    agent = Agent(
        name="test-agent",
        description="A test agent",
        capabilities=["file-operations"]
    )

    manager.save_agent(agent)

    # Verify file exists
    agent_file = tmp_path / "agents" / "test-agent.json"
    assert agent_file.exists()

    # Load and verify
    loaded = manager.load_agent("test-agent")
    assert loaded.name == "test-agent"
    assert loaded.description == "A test agent"
    assert loaded.capabilities == ["file-operations"]


def test_load_nonexistent_agent(tmp_path):
    """Test that loading a nonexistent agent raises FileNotFoundError."""
    manager = AgentManager(base_path=tmp_path)

    try:
        manager.load_agent("does-not-exist")
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError as e:
        assert "does-not-exist" in str(e)


def test_list_agents(tmp_path):
    """Test listing all agents."""
    manager = AgentManager(base_path=tmp_path)

    # Initially empty
    assert manager.list_agents() == []

    # Create some agents
    agent1 = Agent(name="agent-one", description="First")
    agent2 = Agent(name="agent-two", description="Second")
    agent3 = Agent(name="zebra", description="Last alphabetically")

    manager.save_agent(agent1)
    manager.save_agent(agent2)
    manager.save_agent(agent3)

    # List should be sorted
    agents = manager.list_agents()
    assert agents == ["agent-one", "agent-two", "zebra"]


def test_agent_exists(tmp_path):
    """Test checking if an agent exists."""
    manager = AgentManager(base_path=tmp_path)

    assert not manager.agent_exists("test-agent")

    agent = Agent(name="test-agent", description="Test")
    manager.save_agent(agent)

    assert manager.agent_exists("test-agent")


def test_delete_agent(tmp_path):
    """Test deleting an agent."""
    manager = AgentManager(base_path=tmp_path)

    agent = Agent(name="to-delete", description="Will be deleted")
    manager.save_agent(agent)

    # Create a history file too
    history_file = tmp_path / "history" / "to-delete.json"
    history_file.write_text("[]")

    assert manager.agent_exists("to-delete")
    assert history_file.exists()

    manager.delete_agent("to-delete")

    assert not manager.agent_exists("to-delete")
    assert not history_file.exists()


def test_get_and_set_last_agent(tmp_path):
    """Test getting and setting the last used agent."""
    manager = AgentManager(base_path=tmp_path)

    # Initially None
    assert manager.get_last_agent() is None

    # Set last agent
    manager.set_last_agent("my-agent")
    assert manager.get_last_agent() == "my-agent"

    # Update last agent
    manager.set_last_agent("another-agent")
    assert manager.get_last_agent() == "another-agent"

    # Verify config file exists
    assert manager.config_file.exists()


def test_bootstrap_creates_agent_builder(tmp_path):
    """Test that bootstrap creates the agent-builder agent."""
    manager = AgentManager(base_path=tmp_path)

    assert not manager.agent_exists("agent-builder")

    agent = manager.bootstrap()

    assert agent.name == "agent-builder"
    assert "agent-creation" in agent.capabilities
    assert "file-operations" in agent.capabilities
    assert "code-execution" in agent.capabilities
    assert agent.system_prompt != ""

    # Verify it was saved
    assert manager.agent_exists("agent-builder")

    # Verify it was set as last agent
    assert manager.get_last_agent() == "agent-builder"


def test_bootstrap_is_idempotent(tmp_path):
    """Test that calling bootstrap multiple times works correctly."""
    manager = AgentManager(base_path=tmp_path)

    agent1 = manager.bootstrap()
    agent2 = manager.bootstrap()

    # Should overwrite and return same definition
    assert agent1.name == agent2.name
    assert agent1.capabilities == agent2.capabilities
