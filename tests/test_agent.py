"""Tests for the Agent data model."""

from aba.agent import Agent


def test_agent_creation_with_defaults():
    """Test creating an agent with default values."""
    agent = Agent(
        name="test-agent",
        description="A test agent"
    )

    assert agent.name == "test-agent"
    assert agent.description == "A test agent"
    assert agent.version == "1.0"
    assert agent.capabilities == []
    assert agent.system_prompt == ""
    assert agent.config["model"] == "openai/gpt-4o-mini"
    assert agent.config["preserve_history"] is True


def test_agent_creation_with_capabilities():
    """Test creating an agent with specific capabilities."""
    agent = Agent(
        name="code-reviewer",
        description="Reviews code",
        capabilities=["file-operations", "code-execution"]
    )

    assert agent.capabilities == ["file-operations", "code-execution"]


def test_agent_to_dict():
    """Test serializing agent to dictionary."""
    agent = Agent(
        name="test-agent",
        description="A test agent",
        capabilities=["web-access"],
        system_prompt="You are a helpful assistant."
    )

    data = agent.to_dict()

    assert data["name"] == "test-agent"
    assert data["description"] == "A test agent"
    assert data["capabilities"] == ["web-access"]
    assert data["system_prompt"] == "You are a helpful assistant."
    assert "config" in data
    assert "metadata" in data


def test_agent_from_dict():
    """Test deserializing agent from dictionary."""
    data = {
        "name": "research-bot",
        "description": "A research assistant",
        "version": "1.0",
        "capabilities": ["web-access"],
        "system_prompt": "I help with research.",
        "config": {
            "model": "openai/gpt-4o-mini",
            "temperature": 0.8
        }
    }

    agent = Agent.from_dict(data)

    assert agent.name == "research-bot"
    assert agent.description == "A research assistant"
    assert agent.capabilities == ["web-access"]
    assert agent.system_prompt == "I help with research."
    assert agent.config["temperature"] == 0.8


def test_agent_round_trip_serialization():
    """Test that agent can be serialized and deserialized without data loss."""
    original = Agent(
        name="round-trip-test",
        description="Testing serialization",
        capabilities=["agent-creation", "file-operations"],
        system_prompt="Test prompt"
    )

    data = original.to_dict()
    restored = Agent.from_dict(data)

    assert restored.name == original.name
    assert restored.description == original.description
    assert restored.capabilities == original.capabilities
    assert restored.system_prompt == original.system_prompt
