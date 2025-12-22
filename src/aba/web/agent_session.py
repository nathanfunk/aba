"""Async agent session manager for WebSocket chat."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from fastapi import WebSocket

from ..agent import Agent
from ..agent_manager import AgentManager
from ..capabilities import CAPABILITIES
from ..tool_schema import ToolSchema
from ..tools import TOOL_SCHEMAS
from .streaming_model import StreamingOpenRouterModel

logger = logging.getLogger(__name__)


class AgentSession:
    """Manages a single agent chat session over WebSocket.

    This is the async equivalent of AgentRuntime, designed for web usage.
    It handles streaming LLM responses, tool execution, and history management.
    """

    def __init__(
        self,
        agent: Agent,
        manager: AgentManager,
        websocket: WebSocket
    ):
        """Initialize the session.

        Args:
            agent: Agent to run
            manager: AgentManager for persistence
            websocket: WebSocket connection
        """
        logger.info(f"Initializing AgentSession for agent '{agent.name}'")
        self.agent = agent
        self.manager = manager
        self.websocket = websocket
        self.tool_schemas = self._load_tools()
        self.history = self._load_history()
        self.model = self._create_model()
        self.current_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        logger.info(f"Session initialized with {len(self.tool_schemas)} tools, {len(self.history)} history items")

    def _load_tools(self) -> dict[str, ToolSchema]:
        """Load tool schemas based on agent capabilities.

        Returns:
            Dictionary mapping tool names to ToolSchema objects
        """
        tools = {}

        for capability_name in self.agent.capabilities:
            if capability_name not in CAPABILITIES:
                continue

            capability = CAPABILITIES[capability_name]
            for tool_name in capability.tools:
                if tool_name in TOOL_SCHEMAS:
                    tools[tool_name] = TOOL_SCHEMAS[tool_name]

        # Always include get_context_info
        if "get_context_info" in TOOL_SCHEMAS:
            tools["get_context_info"] = TOOL_SCHEMAS["get_context_info"]

        return tools

    def _create_model(self) -> StreamingOpenRouterModel:
        """Create streaming language model for this agent.

        Returns:
            Configured streaming model
        """
        return StreamingOpenRouterModel(
            model=self.agent.config.get("model", "openai/gpt-4o-mini"),
            temperature=self.agent.config.get("temperature", 0.7)
        )

    def _load_history(self) -> list[tuple[str, str, dict]]:
        """Load chat history with tool call metadata.

        Returns:
            List of (role, message, metadata) tuples where metadata contains
            tool_calls and usage info
        """
        if not self.agent.config.get("preserve_history", True):
            return []

        history_file = self.manager.history_dir / f"{self.agent.name}.json"
        if history_file.exists():
            try:
                with open(history_file) as f:
                    data = json.load(f)
                    result = []
                    for item in data:
                        role = item["role"]
                        message = item["message"]
                        # Support both old and new formats
                        metadata = {
                            "tool_calls": item.get("tool_calls", []),
                            "usage": item.get("usage", {})
                        }
                        result.append((role, message, metadata))
                    return result
            except Exception:
                return []

        return []

    def _save_history(self) -> None:
        """Save chat history with tool call metadata."""
        if not self.agent.config.get("preserve_history", True):
            return

        history_file = self.manager.history_dir / f"{self.agent.name}.json"
        data = []
        for role, msg, metadata in self.history:
            entry = {"role": role, "message": msg}
            # Only include metadata fields if they have content
            if metadata.get("tool_calls"):
                entry["tool_calls"] = metadata["tool_calls"]
            if metadata.get("usage"):
                entry["usage"] = metadata["usage"]
            data.append(entry)

        with open(history_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _format_tool_calls_for_context(self, tool_calls: list[dict]) -> str:
        """Format tool calls for inclusion in LLM context.

        Args:
            tool_calls: List of tool call dicts with tool_name, arguments, result, success

        Returns:
            Formatted string showing tools used
        """
        if not tool_calls:
            return ""

        lines = ["[Tools used:"]
        for tc in tool_calls:
            # Format arguments
            args_str = ", ".join(f"{k}={repr(v)}" for k, v in tc["arguments"].items())

            # Preview result (truncate to 100 chars)
            result_preview = tc["result"][:100]
            if len(tc["result"]) > 100:
                result_preview += "..."

            # Status
            status = "success" if tc["success"] else "error"

            lines.append(f"  {tc['tool_name']}({args_str}) → {status}: {result_preview}]")

        return "\n".join(lines) + "]"

    def _build_system_prompt(self) -> str:
        """Build system prompt from agent's base prompt plus capability additions.

        Returns:
            Complete system prompt
        """
        parts = []

        if self.agent.system_prompt:
            parts.append(self.agent.system_prompt)

        for cap_name in self.agent.capabilities:
            if cap_name in CAPABILITIES:
                parts.append(CAPABILITIES[cap_name].system_prompt_addition)

        return "\n\n".join(parts)

    def _build_tools_array(self) -> list[dict]:
        """Build tools array for OpenRouter function calling API.

        Returns:
            List of tool definitions in OpenRouter format
        """
        return [schema.to_openrouter_format() for schema in self.tool_schemas.values()]

    def _build_messages(self, user_input: str) -> list[dict]:
        """Build messages array for LLM request.

        Args:
            user_input: Current user message

        Returns:
            List of message dictionaries
        """
        messages = []

        # Add system prompt
        system_prompt = self._build_system_prompt()
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Add history (last 10 exchanges = 20 messages)
        for role, message, metadata in self.history[-20:]:
            api_role = "user" if role == "user" else "assistant"

            # For agent messages with tool calls, append tool summary to content
            content = message
            if role == "agent" and metadata.get("tool_calls"):
                tool_summary = self._format_tool_calls_for_context(metadata["tool_calls"])
                content = f"{message}\n\n{tool_summary}"

            messages.append({"role": api_role, "content": content})

        # Add current user input
        messages.append({"role": "user", "content": user_input})

        return messages

    async def send_message(self, message: dict) -> None:
        """Send a message to the client via WebSocket.

        Args:
            message: Message dictionary to send
        """
        try:
            await self.websocket.send_json(message)
        except Exception as e:
            # WebSocket closed or error
            logger.warning(f"Failed to send message to WebSocket: {type(e).__name__}: {e}")

    async def handle_user_message(self, user_input: str) -> None:
        """Process user message with streaming response.

        This is the main chat orchestration method that:
        1. Builds messages array
        2. Streams LLM response
        3. Executes tools if requested
        4. Saves history

        Args:
            user_input: User's message
        """
        logger.info(f"Handling user message (length={len(user_input)})")

        # Build messages
        messages = self._build_messages(user_input)
        tools = self._build_tools_array() if self.tool_schemas else None

        # Track accumulated content and tool calls for history
        accumulated_content = ""
        accumulated_tool_calls = []

        # Tool execution loop (max 10 iterations)
        max_iterations = 10
        for iteration in range(max_iterations):
            logger.debug(f"Tool execution loop iteration {iteration + 1}/{max_iterations}")
            try:
                # Stream from LLM
                async for chunk in self.model.chat_stream(messages, tools=tools):
                    chunk_type = chunk.get("type")

                    if chunk_type == "content":
                        # Stream text to client
                        delta = chunk["delta"]
                        accumulated_content += delta
                        await self.send_message({
                            "type": "stream_chunk",
                            "content": delta,
                            "is_complete": False
                        })

                    elif chunk_type == "tool_calls":
                        # Execute tools
                        tool_calls = chunk["calls"]
                        logger.info(f"Received {len(tool_calls)} tool calls")

                        # Add assistant message with tool calls to messages
                        messages.append({
                            "role": "assistant",
                            "content": accumulated_content or None,
                            "tool_calls": tool_calls
                        })

                        # Execute each tool
                        for tool_call in tool_calls:
                            tool_name = tool_call["function"]["name"]
                            tool_args_str = tool_call["function"]["arguments"]
                            tool_call_id = tool_call["id"]

                            try:
                                # Parse arguments
                                tool_args = json.loads(tool_args_str)
                                logger.info(f"Executing tool: {tool_name} with args: {tool_args}")

                                # Send tool start notification
                                display_args = {k: v for k, v in tool_args.items() if not k.startswith("_")}
                                await self.send_message({
                                    "type": "tool_start",
                                    "tool_name": tool_name,
                                    "arguments": display_args
                                })

                                # Execute tool
                                if tool_name not in self.tool_schemas:
                                    result = f"Error: Tool '{tool_name}' not found"
                                    success = False
                                    logger.error(f"Tool '{tool_name}' not found in available tools")
                                else:
                                    schema = self.tool_schemas[tool_name]

                                    # Inject special parameters
                                    if "_manager" in schema.function.__code__.co_varnames:
                                        tool_args["_manager"] = self.manager
                                    if "_runtime" in schema.function.__code__.co_varnames:
                                        tool_args["_runtime"] = self

                                    # Run synchronous tool in thread pool
                                    logger.debug(f"Running tool {tool_name} in thread pool")
                                    result = await asyncio.to_thread(
                                        schema.function,
                                        **tool_args
                                    )
                                    success = True
                                    logger.info(f"Tool {tool_name} completed successfully")

                            except json.JSONDecodeError as e:
                                result = f"Error: Invalid JSON arguments: {e}"
                                success = False
                                logger.error(f"JSON decode error for tool {tool_name}: {e}")
                            except TypeError as e:
                                result = f"Error: Invalid arguments: {e}"
                                success = False
                                logger.error(f"Type error executing tool {tool_name}: {e}")
                            except Exception as e:
                                result = f"Error executing tool: {e}"
                                success = False
                                logger.error(f"Unexpected error executing tool {tool_name}: {e}", exc_info=True)

                            # Send tool result to client
                            await self.send_message({
                                "type": "tool_result",
                                "tool_name": tool_name,
                                "result": str(result),
                                "success": success
                            })

                            # Record tool call details for history
                            result_str = str(result)
                            accumulated_tool_calls.append({
                                "tool_name": tool_name,
                                "arguments": display_args,  # Already filtered from _manager/_runtime
                                "result": result_str[:1000],  # Truncate long results
                                "success": not result_str.startswith("Error"),
                                "result_length": len(result_str)
                            })

                            # Add tool result to messages
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call_id,
                                "content": str(result)
                            })

                        # Reset accumulated content for next iteration
                        accumulated_content = ""

                        # Continue loop to get next response
                        break  # Break inner async for loop to start next iteration

                    elif chunk_type == "done":
                        # Completion - send final messages
                        logger.info("Stream complete, sending final message")
                        await self.send_message({
                            "type": "stream_chunk",
                            "content": "",
                            "is_complete": True
                        })

                        usage = chunk.get("usage", {
                            "prompt_tokens": 0,
                            "completion_tokens": 0,
                            "total_tokens": 0
                        })
                        self.current_usage = usage

                        await self.send_message({
                            "type": "agent_message",
                            "content": accumulated_content,
                            "usage": usage
                        })

                        # Save to history with metadata
                        self.history.append(("user", user_input, {}))
                        metadata = {
                            "tool_calls": accumulated_tool_calls,
                            "usage": usage
                        }
                        self.history.append(("agent", accumulated_content, metadata))
                        self._save_history()
                        logger.debug(f"History saved (total items: {len(self.history)})")

                        # Exit tool execution loop
                        return

                    elif chunk_type == "error":
                        # Error occurred
                        logger.error(f"Error from streaming model: {chunk['message']}")
                        await self.send_message({
                            "type": "error",
                            "message": chunk["message"],
                            "recoverable": True
                        })
                        return

                # If we get here, we finished streaming but need to continue tool loop
                # (happens when tool_calls is the last chunk)

            except Exception as e:
                # Unexpected error
                logger.error(f"Unexpected error in handle_user_message: {type(e).__name__}: {e}", exc_info=True)
                await self.send_message({
                    "type": "error",
                    "message": f"Session error: {str(e)}",
                    "recoverable": False
                })
                return

        # Max iterations reached
        logger.warning(f"Tool execution limit reached ({max_iterations} iterations)")
        await self.send_message({
            "type": "error",
            "message": "Tool execution limit reached (10 iterations)",
            "recoverable": False
        })

    def clear_history(self) -> None:
        """Clear chat history."""
        self.history.clear()
        self._save_history()
