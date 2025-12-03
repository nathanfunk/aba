"""FastAPI web server for Agent Builder."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from ..agent_manager import AgentManager
from .agent_session import AgentSession


app = FastAPI(
    title="ABA Web Interface",
    description="Web interface for Agent Builder (aba)",
    version="1.0.0"
)

# Enable CORS for development (frontend on different port)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# REST API endpoints

@app.get("/")
async def root():
    """Root endpoint - check if frontend is built."""
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        return FileResponse(str(static_dir / "index.html"))
    return {
        "message": "ABA Web Interface API",
        "status": "Frontend not built. Run: cd web-ui && npm run build"
    }


@app.get("/api/agents")
async def list_agents():
    """List all available agents.

    Returns:
        Dictionary with agent list and last-used agent name
    """
    manager = AgentManager()
    agent_names = manager.list_agents()
    last_agent = manager.get_last_agent()

    agents_info = []
    for name in agent_names:
        try:
            agent = manager.load_agent(name)
            agents_info.append({
                "name": agent.name,
                "description": agent.description,
                "capabilities": agent.capabilities,
                "created": agent.created,
                "last_used": agent.last_used
            })
        except Exception as e:
            # If agent fails to load, include minimal info
            agents_info.append({
                "name": name,
                "description": f"Error loading agent: {e}",
                "capabilities": [],
                "created": "",
                "last_used": ""
            })

    return {
        "agents": agents_info,
        "last_agent": last_agent
    }


@app.get("/api/agents/{agent_name}")
async def get_agent(agent_name: str):
    """Get details for a specific agent.

    Args:
        agent_name: Name of the agent to retrieve

    Returns:
        Agent details including configuration

    Raises:
        HTTPException: If agent not found
    """
    manager = AgentManager()

    if not manager.agent_exists(agent_name):
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

    try:
        agent = manager.load_agent(agent_name)
        return {
            "name": agent.name,
            "description": agent.description,
            "capabilities": agent.capabilities,
            "system_prompt": agent.system_prompt,
            "config": agent.config,
            "created": agent.created,
            "last_used": agent.last_used,
            "version": agent.version,
            "metadata": agent.metadata
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading agent: {e}")


# WebSocket endpoint (with streaming and tool execution)

@app.websocket("/ws/chat/{agent_name}")
async def websocket_chat(websocket: WebSocket, agent_name: str):
    """WebSocket endpoint for agent chat with streaming support.

    Args:
        websocket: WebSocket connection
        agent_name: Name of the agent to chat with
    """
    await websocket.accept()

    try:
        # Load agent
        manager = AgentManager()

        if not manager.agent_exists(agent_name):
            await websocket.send_json({
                "type": "error",
                "message": f"Agent '{agent_name}' not found",
                "recoverable": False
            })
            await websocket.close()
            return

        agent = manager.load_agent(agent_name)

        # Create session
        session = AgentSession(agent, manager, websocket)

        # Send initial info
        await websocket.send_json({
            "type": "info",
            "message": f"Connected to agent: {agent.name}",
            "capabilities": agent.capabilities,
            "tools": list(session.tool_schemas.keys())
        })

        # Message loop
        while True:
            # Receive message
            data = await websocket.receive_json()

            message_type = data.get("type")

            if message_type == "user_message":
                content = data.get("content", "")
                await session.handle_user_message(content)

            elif message_type == "clear_history":
                session.clear_history()
                await websocket.send_json({
                    "type": "info",
                    "message": "History cleared"
                })

            elif message_type == "get_capabilities":
                await websocket.send_json({
                    "type": "info",
                    "capabilities": agent.capabilities,
                    "tools": list(session.tool_schemas.keys())
                })

            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown message type: {message_type}",
                    "recoverable": True
                })

    except WebSocketDisconnect:
        # Client disconnected - save history
        try:
            session._save_history()
            manager.set_last_agent(agent_name)
        except:
            pass
    except Exception as e:
        # Send error to client if still connected
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"Server error: {str(e)}",
                "recoverable": False
            })
        except:
            pass


# Serve static files (built React app)
# This will be added after frontend is built

static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="assets")


def main():
    """Entry point for aba-web command."""
    import uvicorn

    # Check if frontend is built
    static_dir = Path(__file__).parent / "static"
    if not static_dir.exists():
        print("\n⚠️  WARNING: Frontend not built.")
        print("To build the frontend:")
        print("  cd web-ui")
        print("  npm install")
        print("  npm run build")
        print("\nYou can still test the API and WebSocket endpoints.\n")

    print("🚀 Starting ABA Web Interface...")
    print("📍 Server running at: http://localhost:8000")
    print("📡 WebSocket endpoint: ws://localhost:8000/ws/chat/{agent_name}")
    print("📚 API docs: http://localhost:8000/docs")
    print("\nPress Ctrl+C to stop\n")

    uvicorn.run(
        "aba.web.server:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=True  # Enable auto-reload during development
    )


if __name__ == "__main__":
    main()
