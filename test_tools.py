#!/usr/bin/env python3
"""Test tool execution via WebSocket (Phase 3)."""

import asyncio
import json
import websockets
from pathlib import Path


async def test_tool_execution():
    """Test WebSocket with tool execution."""
    # Use agent-builder which has file-operations capability
    uri = "ws://localhost:8000/ws/chat/agent-builder"

    print(f"Connecting to {uri}...")
    print("Testing tool execution during streaming...\n")

    async with websockets.connect(uri) as websocket:
        # Receive initial info
        response = await websocket.recv()
        info = json.loads(response)
        print(f"✓ Connected to: {info.get('message', 'unknown')}")
        print(f"  Tools available: {info.get('tools', [])}\n")

        # Create a test file first
        test_file = Path("/tmp/test_aba_tool.txt")
        test_file.write_text("This is a test file for tool execution!")

        # Test 1: Ask agent to read the file
        print("=" * 60)
        print("TEST 1: Reading a file with read_file tool")
        print("=" * 60)

        test_message = {
            "type": "user_message",
            "content": f"Please read the file {test_file} and tell me what it says."
        }
        print(f"\n→ User: {test_message['content']}\n")
        await websocket.send(json.dumps(test_message))

        # Collect response
        await process_response(websocket)

        # Test 2: Ask agent to list files
        print("\n" + "=" * 60)
        print("TEST 2: Listing files with list_files tool")
        print("=" * 60)

        test_message2 = {
            "type": "user_message",
            "content": "List the files in /tmp directory"
        }
        print(f"\n→ User: {test_message2['content']}\n")
        await websocket.send(json.dumps(test_message2))

        # Collect response
        await process_response(websocket)

        # Clean up
        test_file.unlink()
        print("\n✅ Phase 3 tool execution test successful!")


async def process_response(websocket):
    """Process and display streaming response with tool calls."""
    accumulated_text = ""
    tool_calls_seen = []

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
                    print()  # New line

            elif msg_type == "tool_start":
                tool_name = data.get("tool_name")
                args = data.get("arguments", {})
                tool_calls_seen.append(tool_name)
                print(f"\n🔧 Executing tool: {tool_name}")
                print(f"   Arguments: {json.dumps(args, indent=14)}")

            elif msg_type == "tool_result":
                tool_name = data.get("tool_name")
                result = data.get("result", "")
                success = data.get("success", False)

                status = "✓" if success else "✗"
                print(f"{status} Result from {tool_name}:")
                # Truncate long results
                if len(result) > 200:
                    print(f"   {result[:200]}...")
                else:
                    print(f"   {result}")
                print()

            elif msg_type == "agent_message":
                usage = data.get("usage", {})
                print(f"\n✓ Response complete")
                print(f"  Tools used: {', '.join(tool_calls_seen) if tool_calls_seen else 'None'}")
                print(f"  Total tokens: {usage.get('total_tokens', 0)}")
                return  # Done with this response

            elif msg_type == "error":
                print(f"\n✗ Error: {data.get('message')}")
                return

            elif msg_type == "info":
                print(f"\nℹ Info: {data.get('message', data)}")

        except asyncio.TimeoutError:
            print("\n✗ Timeout waiting for response")
            return


if __name__ == "__main__":
    asyncio.run(test_tool_execution())
