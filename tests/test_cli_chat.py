"""Tests for the interactive chat helpers."""

from unittest.mock import MagicMock, patch
import argparse

import pytest

from aba.cli import _format_chat_prompt, _run_chat_interface


def test_format_chat_prompt_includes_history() -> None:
    history = [("user", "Hello"), ("agent", "Hi there")]

    prompt = _format_chat_prompt(history)

    assert "Agent Building Agent" in prompt
    assert "User: Hello" in prompt
    assert prompt.strip().endswith("Agent:")


def test_cli_chat_exits_on_exit_command(monkeypatch, capsys):
    """Test that /exit command properly exits the chat loop."""
    inputs = iter(["/exit"])
    monkeypatch.setattr('builtins.input', lambda _: next(inputs))

    args = argparse.Namespace(model="openai/gpt-4o-mini", api_key_env="OPENROUTER_API_KEY")

    with patch('aba.cli.OpenRouterLanguageModel') as mock_model_class:
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        _run_chat_interface(args)

    captured = capsys.readouterr()
    assert "Starting interactive chat" in captured.out
    assert "Exiting chat." in captured.out
    # Should not call the model if we exit immediately
    mock_model.complete.assert_not_called()


def test_cli_chat_exits_on_quit_command(monkeypatch, capsys):
    """Test that /quit command properly exits the chat loop."""
    inputs = iter(["/quit"])
    monkeypatch.setattr('builtins.input', lambda _: next(inputs))

    args = argparse.Namespace(model="openai/gpt-4o-mini", api_key_env="OPENROUTER_API_KEY")

    with patch('aba.cli.OpenRouterLanguageModel') as mock_model_class:
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        _run_chat_interface(args)

    captured = capsys.readouterr()
    assert "Exiting chat." in captured.out


def test_cli_chat_handles_conversation(monkeypatch, capsys):
    """Test that chat handles a conversation with mocked model responses."""
    inputs = iter(["How do I build an agent?", "Thanks!", "/exit"])
    monkeypatch.setattr('builtins.input', lambda _: next(inputs))

    args = argparse.Namespace(model="openai/gpt-4o-mini", api_key_env="OPENROUTER_API_KEY")

    with patch('aba.cli.OpenRouterLanguageModel') as mock_model_class:
        mock_model = MagicMock()
        mock_model.complete.side_effect = [
            "You can start by defining your agent's capabilities.",
            "You're welcome! Let me know if you need more help."
        ]
        mock_model_class.return_value = mock_model

        _run_chat_interface(args)

    captured = capsys.readouterr()
    assert "You can start by defining your agent's capabilities." in captured.out
    assert "You're welcome!" in captured.out
    assert mock_model.complete.call_count == 2


def test_cli_chat_skips_empty_input(monkeypatch, capsys):
    """Test that empty input is skipped without calling the model."""
    inputs = iter(["", "  ", "Hello", "/exit"])
    monkeypatch.setattr('builtins.input', lambda _: next(inputs))

    args = argparse.Namespace(model="openai/gpt-4o-mini", api_key_env="OPENROUTER_API_KEY")

    with patch('aba.cli.OpenRouterLanguageModel') as mock_model_class:
        mock_model = MagicMock()
        mock_model.complete.return_value = "Hi there!"
        mock_model_class.return_value = mock_model

        _run_chat_interface(args)

    # Should only be called once (for "Hello", not for empty strings)
    assert mock_model.complete.call_count == 1


def test_cli_chat_handles_eof(monkeypatch, capsys):
    """Test that EOFError (Ctrl+D) exits gracefully."""
    def raise_eof(_):
        raise EOFError()

    monkeypatch.setattr('builtins.input', raise_eof)

    args = argparse.Namespace(model="openai/gpt-4o-mini", api_key_env="OPENROUTER_API_KEY")

    with patch('aba.cli.OpenRouterLanguageModel') as mock_model_class:
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        _run_chat_interface(args)

    captured = capsys.readouterr()
    assert "Starting interactive chat" in captured.out
    # Should exit gracefully without error


def test_cli_chat_handles_model_error(monkeypatch, capsys):
    """Test that errors from the language model are handled gracefully."""
    inputs = iter(["Hello", "/exit"])
    monkeypatch.setattr('builtins.input', lambda _: next(inputs))

    args = argparse.Namespace(model="openai/gpt-4o-mini", api_key_env="OPENROUTER_API_KEY")

    with patch('aba.cli.OpenRouterLanguageModel') as mock_model_class:
        mock_model = MagicMock()
        mock_model.complete.side_effect = Exception("Network error")
        mock_model_class.return_value = mock_model

        _run_chat_interface(args)

    captured = capsys.readouterr()
    assert "Error contacting language model: Network error" in captured.out
    # Should continue running after error and allow exit
    assert "Exiting chat." in captured.out


def test_cli_chat_preserves_history_after_error(monkeypatch, capsys):
    """Test that conversation history is rolled back after a model error."""
    inputs = iter(["First message", "Second message", "/exit"])
    monkeypatch.setattr('builtins.input', lambda _: next(inputs))

    args = argparse.Namespace(model="openai/gpt-4o-mini", api_key_env="OPENROUTER_API_KEY")

    with patch('aba.cli.OpenRouterLanguageModel') as mock_model_class:
        mock_model = MagicMock()
        # First call fails, second succeeds
        mock_model.complete.side_effect = [
            Exception("Temporary error"),
            "Got your second message!"
        ]
        mock_model_class.return_value = mock_model

        _run_chat_interface(args)

    captured = capsys.readouterr()
    assert "Error contacting language model: Temporary error" in captured.out
    assert "Got your second message!" in captured.out
    # Both messages should have been attempted
    assert mock_model.complete.call_count == 2
