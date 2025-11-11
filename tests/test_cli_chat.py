"""Tests for the interactive chat helpers."""

from aba.cli import _format_chat_prompt


def test_format_chat_prompt_includes_history() -> None:
    history = [("user", "Hello"), ("agent", "Hi there")]

    prompt = _format_chat_prompt(history)

    assert "Agent Building Agent" in prompt
    assert "User: Hello" in prompt
    assert prompt.strip().endswith("Agent:")
