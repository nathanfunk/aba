"""Tests for agent tools."""

from pathlib import Path

from aba.agent_manager import AgentManager
from aba.tools import (
    create_agent,
    delete_agent,
    list_agents,
    read_file,
    write_file,
    list_files,
    delete_file,
)


def test_create_agent(tmp_path):
    """Test creating an agent via tool."""
    manager = AgentManager(base_path=tmp_path)

    result = create_agent(
        name="test-bot",
        description="A test bot",
        capabilities=["file-operations"],
        _manager=manager
    )

    assert "✓ Created agent 'test-bot'" in result
    assert "file-operations" in result
    assert manager.agent_exists("test-bot")

    # Verify agent details
    agent = manager.load_agent("test-bot")
    assert agent.name == "test-bot"
    assert agent.description == "A test bot"
    assert agent.capabilities == ["file-operations"]


def test_create_agent_with_no_capabilities(tmp_path):
    """Test creating a minimal agent with no capabilities."""
    manager = AgentManager(base_path=tmp_path)

    result = create_agent(
        name="minimal-bot",
        description="Minimal agent",
        _manager=manager
    )

    assert "✓ Created agent 'minimal-bot'" in result
    assert "none (chat only)" in result

    agent = manager.load_agent("minimal-bot")
    assert agent.capabilities == []


def test_create_agent_already_exists(tmp_path):
    """Test error when creating duplicate agent."""
    manager = AgentManager(base_path=tmp_path)

    create_agent(name="duplicate", description="First", _manager=manager)
    result = create_agent(name="duplicate", description="Second", _manager=manager)

    assert "Error" in result
    assert "already exists" in result


def test_delete_agent_tool(tmp_path):
    """Test deleting an agent via tool."""
    manager = AgentManager(base_path=tmp_path)

    create_agent(name="to-delete", description="Will be deleted", _manager=manager)
    assert manager.agent_exists("to-delete")

    result = delete_agent("to-delete", _manager=manager)

    assert "✓ Deleted agent 'to-delete'" in result
    assert not manager.agent_exists("to-delete")


def test_delete_agent_not_found(tmp_path):
    """Test error when deleting nonexistent agent."""
    manager = AgentManager(base_path=tmp_path)
    result = delete_agent("does-not-exist", _manager=manager)

    assert "Error" in result
    assert "not found" in result


def test_delete_agent_builder_protected(tmp_path):
    """Test that agent-builder cannot be deleted."""
    manager = AgentManager(base_path=tmp_path)
    manager.bootstrap()

    result = delete_agent("agent-builder", _manager=manager)

    assert "Error" in result
    assert "Cannot delete" in result
    assert manager.agent_exists("agent-builder")


def test_list_agents_tool(tmp_path):
    """Test listing agents via tool."""
    manager = AgentManager(base_path=tmp_path)

    # Empty list
    result = list_agents(_manager=manager)
    assert "No agents found" in result

    # Create some agents
    create_agent("agent-one", "First", _manager=manager)
    create_agent("agent-two", "Second", _manager=manager)

    result = list_agents(_manager=manager)
    assert "agent-one" in result
    assert "agent-two" in result


def test_read_file_tool(tmp_path):
    """Test reading a file via tool."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello, World!")

    result = read_file(str(test_file))
    assert result == "Hello, World!"


def test_read_file_not_found():
    """Test error when reading nonexistent file."""
    result = read_file("/nonexistent/file.txt")
    assert "Error" in result
    assert "not found" in result


def test_write_file_tool(tmp_path):
    """Test writing a file via tool."""
    test_file = tmp_path / "output.txt"

    result = write_file(str(test_file), "Test content")

    assert "✓ Wrote" in result
    assert "12 bytes" in result
    assert test_file.read_text() == "Test content"


def test_list_files_tool(tmp_path):
    """Test listing files via tool."""
    # Create some files
    (tmp_path / "file1.txt").write_text("content")
    (tmp_path / "file2.txt").write_text("content")
    (tmp_path / "subdir").mkdir()

    result = list_files(str(tmp_path))

    assert "file1.txt" in result
    assert "file2.txt" in result
    assert "subdir" in result


def test_list_files_not_found():
    """Test error when listing nonexistent directory."""
    result = list_files("/nonexistent/directory")
    assert "Error" in result
    assert "not found" in result


def test_delete_file_tool(tmp_path):
    """Test deleting a file via tool."""
    test_file = tmp_path / "to_delete.txt"
    test_file.write_text("content")

    result = delete_file(str(test_file))

    assert "✓ Deleted" in result
    assert not test_file.exists()


def test_delete_file_not_found():
    """Test error when deleting nonexistent file."""
    result = delete_file("/nonexistent/file.txt")
    assert "Error" in result
    assert "not found" in result
