"""
Claude Code Web - Local Web Interface for Claude Code CLI.

A web-based interface that runs locally and communicates with
the Claude Code CLI on your machine.
"""
import asyncio
import os
import platform
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
import uvicorn

from models import (
    ChatRequest, ChatResponse, Message, MessageRole, MessageType,
    WorkspaceInfo, SystemInfo, SessionStatus, ProjectConfig
)
from claude_interface import ClaudeCodeInterface, ConversationManager
from websocket_manager import ConnectionManager, StreamHandler

# Initialize app
app = FastAPI(
    title="Claude Code Web",
    description="Local web interface for Claude Code CLI",
    version="1.0.0"
)

# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
claude = ClaudeCodeInterface()
conversation_manager = ConversationManager()
ws_manager = ConnectionManager()
stream_handler = StreamHandler(ws_manager)

# Store active streaming tasks
active_tasks: dict = {}


# ============== API Routes ==============

@app.get("/")
async def root():
    """Serve the main web interface."""
    frontend_path = Path(__file__).parent.parent / "frontend" / "index.html"
    if frontend_path.exists():
        return FileResponse(frontend_path)
    return HTMLResponse(content="<h1>Claude Code Web</h1><p>Frontend not found.</p>")


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "claude_installed": claude.is_installed()
    }


@app.get("/api/system", response_model=SystemInfo)
async def get_system_info():
    """Get system information."""
    return SystemInfo(
        claude_code_version=claude.get_version(),
        claude_code_installed=claude.is_installed(),
        python_version=sys.version,
        platform=platform.platform(),
        working_directory=os.getcwd()
    )


@app.get("/api/workspaces")
async def list_workspaces(
    base_path: str = Query(default="~", description="Base path to scan")
):
    """List available workspaces/directories."""
    base = Path(os.path.expanduser(base_path)).resolve()

    workspaces = []
    try:
        for item in base.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                is_git = (item / ".git").exists()
                git_branch = None

                if is_git:
                    head_file = item / ".git" / "HEAD"
                    if head_file.exists():
                        content = head_file.read_text().strip()
                        if content.startswith("ref: refs/heads/"):
                            git_branch = content.replace("ref: refs/heads/", "")

                workspaces.append(WorkspaceInfo(
                    path=str(item),
                    name=item.name,
                    is_git_repo=is_git,
                    git_branch=git_branch,
                    files_count=len(list(item.glob("*")))
                ))
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")

    return sorted(workspaces, key=lambda x: x.name)


@app.get("/api/workspace/files")
async def list_workspace_files(
    workspace: str = Query(..., description="Workspace path"),
    pattern: str = Query(default="*", description="Glob pattern")
):
    """List files in a workspace."""
    workspace_path = Path(os.path.expanduser(workspace)).resolve()

    if not workspace_path.exists():
        raise HTTPException(status_code=404, detail="Workspace not found")

    files = []
    for item in workspace_path.glob(pattern):
        if not any(part.startswith('.') for part in item.parts):
            files.append({
                "path": str(item),
                "name": item.name,
                "is_dir": item.is_dir(),
                "size": item.stat().st_size if item.is_file() else 0
            })

    return sorted(files, key=lambda x: (not x["is_dir"], x["name"]))


# ============== Conversation Routes ==============

@app.get("/api/conversations")
async def list_conversations():
    """List all conversations."""
    return conversation_manager.list_conversations()


@app.post("/api/conversations")
async def create_conversation(workspace: str = Query(default=".")):
    """Create a new conversation."""
    conv_id = conversation_manager.create_conversation(workspace)
    return {"conversation_id": conv_id}


@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get a specific conversation."""
    conv = conversation_manager.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation."""
    if conversation_manager.delete_conversation(conversation_id):
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Conversation not found")


# ============== Chat Routes ==============

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    Send a message to Claude Code (non-streaming).
    For streaming, use the WebSocket endpoint.
    """
    if not claude.is_installed():
        raise HTTPException(
            status_code=503,
            detail="Claude Code CLI is not installed"
        )

    # Create or get conversation
    if request.conversation_id:
        conv_id = request.conversation_id
    else:
        conv_id = conversation_manager.create_conversation(request.workspace)

    # Add user message
    conversation_manager.add_message(conv_id, "user", request.message)

    # Execute command
    result = await claude.execute_command(request.message, request.workspace)

    # Format response
    if result["success"]:
        response_content = result.get("output", {})
        if isinstance(response_content, dict):
            response_text = response_content.get("raw_output", str(response_content))
        else:
            response_text = str(response_content)
    else:
        response_text = result.get("error", "Unknown error")

    # Add assistant message
    conversation_manager.add_message(conv_id, "assistant", response_text)

    return ChatResponse(
        conversation_id=conv_id,
        message=Message(
            role=MessageRole.ASSISTANT,
            content=response_text,
            message_type=MessageType.TEXT
        ),
        status=SessionStatus.IDLE
    )


@app.post("/api/chat/cancel/{conversation_id}")
async def cancel_chat(conversation_id: str):
    """Cancel an active chat session."""
    if conversation_id in active_tasks:
        active_tasks[conversation_id].cancel()
        del active_tasks[conversation_id]

    await claude.cancel(conversation_id)

    return {"status": "cancelled"}


# ============== WebSocket Routes ==============

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """
    WebSocket endpoint for real-time streaming.

    Messages from client:
    - {"action": "chat", "message": "...", "workspace": "...", "conversation_id": "..."}
    - {"action": "subscribe", "conversation_id": "..."}
    - {"action": "unsubscribe", "conversation_id": "..."}
    - {"action": "cancel", "conversation_id": "..."}
    """
    await ws_manager.connect(websocket, client_id)

    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            if action == "chat":
                await handle_chat_message(client_id, data)

            elif action == "subscribe":
                conv_id = data.get("conversation_id")
                if conv_id:
                    await ws_manager.subscribe(client_id, conv_id)
                    await ws_manager.send_personal_message(
                        {"event": "subscribed", "conversation_id": conv_id},
                        client_id
                    )

            elif action == "unsubscribe":
                conv_id = data.get("conversation_id")
                if conv_id:
                    await ws_manager.unsubscribe(client_id, conv_id)
                    await ws_manager.send_personal_message(
                        {"event": "unsubscribed", "conversation_id": conv_id},
                        client_id
                    )

            elif action == "cancel":
                conv_id = data.get("conversation_id")
                if conv_id and conv_id in active_tasks:
                    active_tasks[conv_id].cancel()
                    await ws_manager.send_personal_message(
                        {"event": "cancelled", "conversation_id": conv_id},
                        client_id
                    )

            elif action == "ping":
                await ws_manager.send_personal_message(
                    {"event": "pong", "timestamp": datetime.now().isoformat()},
                    client_id
                )

    except WebSocketDisconnect:
        await ws_manager.disconnect(client_id)


async def handle_chat_message(client_id: str, data: dict):
    """Handle a chat message from WebSocket."""
    message = data.get("message", "")
    workspace = data.get("workspace", ".")
    conversation_id = data.get("conversation_id")

    if not message:
        await ws_manager.send_personal_message(
            {"event": "error", "message": "Empty message"},
            client_id
        )
        return

    # Create conversation if needed
    if not conversation_id:
        conversation_id = conversation_manager.create_conversation(workspace)

    # Subscribe client to conversation
    await ws_manager.subscribe(client_id, conversation_id)

    # Add user message
    conversation_manager.add_message(conversation_id, "user", message)

    # Send acknowledgment
    await ws_manager.send_personal_message(
        {
            "event": "message_received",
            "conversation_id": conversation_id,
            "timestamp": datetime.now().isoformat()
        },
        client_id
    )

    # Start streaming response
    async def stream_task():
        try:
            await stream_handler.stream_response(
                conversation_id,
                claude.chat_stream(message, workspace, conversation_id),
                client_id
            )
        except asyncio.CancelledError:
            await ws_manager.send_personal_message(
                {"event": "cancelled", "conversation_id": conversation_id},
                client_id
            )
        except Exception as e:
            await ws_manager.send_personal_message(
                {"event": "error", "message": str(e), "conversation_id": conversation_id},
                client_id
            )

    # Create and store task
    task = asyncio.create_task(stream_task())
    active_tasks[conversation_id] = task


# ============== Static Files ==============

# Mount static files
frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir / "static")), name="static")


# ============== Main ==============

def main():
    """Run the server."""
    import argparse

    parser = argparse.ArgumentParser(description="Claude Code Web Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    args = parser.parse_args()

    print(f"""
╔═══════════════════════════════════════════════════════════════╗
║                    Claude Code Web                             ║
║                 Local Web Interface                            ║
╠═══════════════════════════════════════════════════════════════╣
║  Server: http://{args.host}:{args.port:<5}                              ║
║  Claude CLI: {"✓ Installed" if claude.is_installed() else "✗ Not found":<20}                      ║
╚═══════════════════════════════════════════════════════════════╝
""")

    uvicorn.run(
        "main:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )


if __name__ == "__main__":
    main()
