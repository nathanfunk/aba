#!/usr/bin/env python3
"""Simple WebSocket test client for Phase 1."""

import asyncio
import json
import websockets


async def test_websocket():
    """Test WebSocket connection and echo functionality."""
    uri = "ws://localhost:8000/ws/chat/agent-builder"

    print(f"Connecting to {uri}...")

    async with websockets.connect(uri) as websocket:
        # Receive initial info message
        response = await websocket.recv()
        print(f"\n← Received: {response}")

        # Send a test message
        test_message = {
            "type": "user_message",
            "content": "Hello, agent!"
        }
        print(f"\n→ Sending: {json.dumps(test_message, indent=2)}")
        await websocket.send(json.dumps(test_message))

        # Receive echo responses
        for _ in range(3):  # Expect 3 messages: 2 stream_chunk + 1 agent_message
            response = await websocket.recv()
            data = json.loads(response)
            print(f"\n← Received ({data['type']}): {json.dumps(data, indent=2)}")

        # Test get_capabilities
        capabilities_msg = {"type": "get_capabilities"}
        print(f"\n→ Sending: {json.dumps(capabilities_msg, indent=2)}")
        await websocket.send(json.dumps(capabilities_msg))

        response = await websocket.recv()
        print(f"\n← Received: {json.dumps(json.loads(response), indent=2)}")

        print("\n✅ WebSocket test successful!")


if __name__ == "__main__":
    asyncio.run(test_websocket())
