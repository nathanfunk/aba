"""WebSocket message protocol definitions.

This module defines the message types and formats for WebSocket communication
between the frontend and backend.
"""

from __future__ import annotations
from typing import Any, Literal
from dataclasses import dataclass


# Client → Server message types
@dataclass
class UserMessage:
    """User sends a chat message."""

    type: Literal["user_message"] = "user_message"
    content: str = ""


@dataclass
class ClearHistoryMessage:
    """User requests to clear chat history."""

    type: Literal["clear_history"] = "clear_history"


@dataclass
class GetCapabilitiesMessage:
    """User requests agent capabilities info."""

    type: Literal["get_capabilities"] = "get_capabilities"


# Server → Client message types
@dataclass
class StreamChunk:
    """Streaming text chunk from LLM."""

    type: Literal["stream_chunk"] = "stream_chunk"
    content: str = ""
    is_complete: bool = False


@dataclass
class ToolStart:
    """Tool execution started."""

    type: Literal["tool_start"] = "tool_start"
    tool_name: str = ""
    arguments: dict[str, Any] | None = None


@dataclass
class ToolResult:
    """Tool execution result."""

    type: Literal["tool_result"] = "tool_result"
    tool_name: str = ""
    result: str = ""
    success: bool = True


@dataclass
class AgentMessage:
    """Complete agent response with usage stats."""

    type: Literal["agent_message"] = "agent_message"
    content: str = ""
    usage: dict[str, int] | None = None


@dataclass
class ErrorMessage:
    """Error occurred."""

    type: Literal["error"] = "error"
    message: str = ""
    recoverable: bool = True


@dataclass
class InfoMessage:
    """System info (capabilities, tools, etc.)."""

    type: Literal["info"] = "info"
    capabilities: list[str] | None = None
    tools: list[str] | None = None
    message: str | None = None
