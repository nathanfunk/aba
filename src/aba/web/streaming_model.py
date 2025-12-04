"""Async OpenRouter language model with SSE streaming support."""

from __future__ import annotations

import json
import logging
import os
from typing import AsyncIterator, Any
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass
class StreamingOpenRouterModel:
    """Async wrapper for OpenRouter with SSE streaming support.

    This model streams responses from OpenRouter's API in real-time,
    parsing Server-Sent Events (SSE) and yielding chunks as they arrive.
    """

    model: str = "openai/gpt-4o-mini"
    temperature: float = 0.7
    api_key_env: str = "OPENROUTER_API_KEY"
    base_url: str = "https://openrouter.ai/api/v1/chat/completions"
    timeout: float = 60.0

    async def chat_stream(
        self,
        messages: list[dict],
        tools: list[dict] | None = None
    ) -> AsyncIterator[dict]:
        """Stream chat responses from OpenRouter.

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            tools: Optional list of tool definitions for function calling

        Yields:
            Dictionaries with different types:
            - {"type": "content", "delta": str} - Text content chunk
            - {"type": "tool_calls", "calls": [...]} - Tool calls (accumulated)
            - {"type": "done", "usage": {...}} - Completion with usage stats
            - {"type": "error", "message": str} - Error occurred
        """
        logger.info(f"Starting chat stream with model={self.model}, tools={'yes' if tools else 'no'}")

        api_key = os.getenv(self.api_key_env)
        if not api_key:
            logger.error(f"API key not found in environment variable {self.api_key_env}")
            yield {
                "type": "error",
                "message": f"OpenRouter API key not found. Set {self.api_key_env} environment variable."
            }
            return

        # Build request body
        request_body = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "stream": True,
            "stream_options": {"include_usage": True}  # Get token counts
        }

        if tools:
            request_body["tools"] = tools
            request_body["tool_choice"] = "auto"

        # Accumulator for tool calls (they come in chunks)
        tool_calls_accumulator: dict[int, dict[str, Any]] = {}

        try:
            logger.debug(f"Sending request to OpenRouter API with {len(messages)} messages")
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://github.com/nathanfunk/aba",
                        "X-Title": "Agent Building Agent - Web Interface",
                    },
                    json=request_body
                ) as response:
                    # Check for HTTP errors
                    if response.status_code != 200:
                        error_text = await response.aread()
                        logger.error(f"OpenRouter API error: status={response.status_code}, body={error_text.decode()}")
                        yield {
                            "type": "error",
                            "message": f"OpenRouter API error ({response.status_code}): {error_text.decode()}"
                        }
                        return

                    logger.debug("Successfully connected to OpenRouter streaming API")

                    # Parse SSE stream
                    async for line in response.aiter_lines():
                        # Skip empty lines and comments
                        if not line or line.startswith(":"):
                            continue

                        # Parse SSE format: "data: {json}"
                        if line.startswith("data: "):
                            data_str = line[6:]  # Remove "data: " prefix

                            # Check for end marker
                            if data_str == "[DONE]":
                                break

                            try:
                                chunk = json.loads(data_str)
                            except json.JSONDecodeError as e:
                                yield {
                                    "type": "error",
                                    "message": f"Failed to parse SSE chunk: {e}"
                                }
                                continue

                            # Check for error in chunk
                            if "error" in chunk:
                                error_msg = chunk["error"].get("message", "Unknown error")
                                logger.error(f"Error in streaming chunk: {error_msg}")
                                yield {
                                    "type": "error",
                                    "message": error_msg
                                }
                                return

                            # Extract delta from chunk
                            try:
                                choice = chunk["choices"][0]
                                delta = choice.get("delta", {})
                                finish_reason = choice.get("finish_reason")

                                # Handle content delta
                                if "content" in delta and delta["content"]:
                                    yield {
                                        "type": "content",
                                        "delta": delta["content"]
                                    }

                                # Handle tool calls delta
                                if "tool_calls" in delta:
                                    for tool_call_delta in delta["tool_calls"]:
                                        index = tool_call_delta.get("index", 0)

                                        # Initialize accumulator for this index
                                        if index not in tool_calls_accumulator:
                                            tool_calls_accumulator[index] = {
                                                "id": "",
                                                "type": "function",
                                                "function": {
                                                    "name": "",
                                                    "arguments": ""
                                                }
                                            }

                                        # Accumulate tool call data
                                        if "id" in tool_call_delta:
                                            tool_calls_accumulator[index]["id"] = tool_call_delta["id"]

                                        if "type" in tool_call_delta:
                                            tool_calls_accumulator[index]["type"] = tool_call_delta["type"]

                                        if "function" in tool_call_delta:
                                            func = tool_call_delta["function"]
                                            if "name" in func:
                                                tool_calls_accumulator[index]["function"]["name"] = func["name"]
                                            if "arguments" in func:
                                                tool_calls_accumulator[index]["function"]["arguments"] += func["arguments"]

                                # Handle completion
                                if finish_reason:
                                    logger.debug(f"Stream finished with reason: {finish_reason}")
                                    if finish_reason == "tool_calls":
                                        # Yield accumulated tool calls
                                        calls = [
                                            tool_calls_accumulator[i]
                                            for i in sorted(tool_calls_accumulator.keys())
                                        ]
                                        logger.info(f"Yielding {len(calls)} tool calls")
                                        yield {
                                            "type": "tool_calls",
                                            "calls": calls
                                        }

                                    # Check for usage stats
                                    usage = chunk.get("usage")
                                    if usage:
                                        logger.info(f"Stream complete. Usage: {usage.get('total_tokens', 0)} tokens")
                                        yield {
                                            "type": "done",
                                            "finish_reason": finish_reason,
                                            "usage": usage
                                        }
                                    else:
                                        logger.info("Stream complete (no usage stats)")
                                        yield {
                                            "type": "done",
                                            "finish_reason": finish_reason,
                                            "usage": {
                                                "prompt_tokens": 0,
                                                "completion_tokens": 0,
                                                "total_tokens": 0
                                            }
                                        }

                            except (KeyError, IndexError, TypeError) as e:
                                # Malformed chunk - log but continue
                                yield {
                                    "type": "error",
                                    "message": f"Malformed chunk: {e}"
                                }
                                continue

        except httpx.TimeoutException as e:
            logger.error(f"OpenRouter request timed out after {self.timeout} seconds: {e}")
            yield {
                "type": "error",
                "message": f"Request timed out after {self.timeout} seconds"
            }
        except httpx.RemoteProtocolError as e:
            logger.error(f"Remote protocol error (connection closed): {e}")
            yield {
                "type": "error",
                "message": f"Connection error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Unexpected streaming error: {type(e).__name__}: {e}", exc_info=True)
            yield {
                "type": "error",
                "message": f"Streaming error: {str(e)}"
            }
