"""
WebSocket connection manager for real-time streaming.
"""
import asyncio
import json
from typing import Dict, Set, Optional
from fastapi import WebSocket
from datetime import datetime


class ConnectionManager:
    """Manage WebSocket connections."""

    def __init__(self):
        # Active connections: {client_id: WebSocket}
        self.active_connections: Dict[str, WebSocket] = {}
        # Conversation subscriptions: {conversation_id: set of client_ids}
        self.subscriptions: Dict[str, Set[str]] = {}
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections[client_id] = websocket

    async def disconnect(self, client_id: str):
        """Handle WebSocket disconnection."""
        async with self._lock:
            if client_id in self.active_connections:
                del self.active_connections[client_id]
            # Remove from all subscriptions
            for conv_id in list(self.subscriptions.keys()):
                self.subscriptions[conv_id].discard(client_id)
                if not self.subscriptions[conv_id]:
                    del self.subscriptions[conv_id]

    async def subscribe(self, client_id: str, conversation_id: str):
        """Subscribe a client to a conversation."""
        async with self._lock:
            if conversation_id not in self.subscriptions:
                self.subscriptions[conversation_id] = set()
            self.subscriptions[conversation_id].add(client_id)

    async def unsubscribe(self, client_id: str, conversation_id: str):
        """Unsubscribe a client from a conversation."""
        async with self._lock:
            if conversation_id in self.subscriptions:
                self.subscriptions[conversation_id].discard(client_id)

    async def send_personal_message(self, message: dict, client_id: str):
        """Send a message to a specific client."""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json(message)
            except Exception:
                await self.disconnect(client_id)

    async def broadcast_to_conversation(self, message: dict, conversation_id: str):
        """Broadcast a message to all clients subscribed to a conversation."""
        if conversation_id not in self.subscriptions:
            return

        disconnected = []
        for client_id in self.subscriptions[conversation_id]:
            if client_id in self.active_connections:
                try:
                    await self.active_connections[client_id].send_json(message)
                except Exception:
                    disconnected.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected:
            await self.disconnect(client_id)

    async def broadcast(self, message: dict):
        """Broadcast a message to all connected clients."""
        disconnected = []
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(client_id)

        for client_id in disconnected:
            await self.disconnect(client_id)

    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.active_connections)


class StreamHandler:
    """Handle streaming responses from Claude Code."""

    def __init__(self, manager: ConnectionManager):
        self.manager = manager

    async def stream_response(
        self,
        conversation_id: str,
        async_generator,
        client_id: Optional[str] = None
    ):
        """
        Stream Claude Code responses to connected clients.

        Args:
            conversation_id: The conversation ID
            async_generator: Async generator yielding response chunks
            client_id: Optional specific client to send to
        """
        full_response = []

        async for chunk in async_generator:
            message = {
                "event": "chunk",
                "conversation_id": conversation_id,
                "timestamp": datetime.now().isoformat(),
                "data": chunk
            }

            if client_id:
                await self.manager.send_personal_message(message, client_id)
            else:
                await self.manager.broadcast_to_conversation(message, conversation_id)

            # Collect full response
            if chunk.get("type") == "text":
                full_response.append(chunk.get("content", ""))

            # Small delay to prevent overwhelming the client
            await asyncio.sleep(0.01)

        # Send completion message
        completion_message = {
            "event": "complete",
            "conversation_id": conversation_id,
            "timestamp": datetime.now().isoformat(),
            "data": {
                "full_response": "".join(full_response)
            }
        }

        if client_id:
            await self.manager.send_personal_message(completion_message, client_id)
        else:
            await self.manager.broadcast_to_conversation(completion_message, conversation_id)
