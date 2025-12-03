#!/usr/bin/env python3
"""Test OpenRouter streaming integration (Phase 2)."""

import asyncio
import json
import websockets


async def test_streaming():
    """Test WebSocket connection with real LLM streaming."""
    uri = "ws://localhost:8000/ws/chat/greater"  # Using 'greater' agent (no capabilities)

    print(f"Connecting to {uri}...")
    print("Testing streaming LLM responses...\n")

    async with websockets.connect(uri) as websocket:
        # Receive initial info message
        response = await websocket.recv()
        info = json.loads(response)
        print(f"✓ Connected to agent: {info.get('message', 'unknown')}")
        print(f"  Capabilities: {info.get('capabilities', [])}")
        print(f"  Tools: {info.get('tools', [])}\n")

        # Send a test message
        test_message = {
            "type": "user_message",
            "content": "Say hello in exactly 5 words!"
        }
        print(f"→ Sending: {test_message['content']}")
        await websocket.send(json.dumps(test_message))

        # Collect streaming response
        print("\n← Streaming response:")
        accumulated_text = ""

        while True:
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                data = json.loads(response)
                msg_type = data.get("type")

                if msg_type == "stream_chunk":
                    content = data.get("content", "")
                    is_complete = data.get("is_complete", False)

                    if content:
                        print(content, end="", flush=True)
                        accumulated_text += content

                    if is_complete:
                        print()  # New line after streaming complete
                        print("\n✓ Streaming complete")

                elif msg_type == "agent_message":
                    usage = data.get("usage", {})
                    print(f"\n✓ Agent message received:")
                    print(f"  Content: {data.get('content', '')[:50]}...")
                    print(f"  Usage: {usage.get('total_tokens', 0)} tokens")
                    print(f"    Prompt: {usage.get('prompt_tokens', 0)}")
                    print(f"    Completion: {usage.get('completion_tokens', 0)}")
                    break  # End of response

                elif msg_type == "error":
                    print(f"\n✗ Error: {data.get('message')}")
                    return

                elif msg_type == "info":
                    print(f"\nℹ Info: {data.get('message', data)}")

            except asyncio.TimeoutError:
                print("\n✗ Timeout waiting for response")
                return

        print("\n✅ Phase 2 streaming test successful!")


if __name__ == "__main__":
    asyncio.run(test_streaming())
