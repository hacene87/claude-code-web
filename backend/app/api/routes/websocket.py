"""
WebSocket Routes
================

Real-time event streaming via WebSocket.
Implements FR-API-002.
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt
import structlog

from app.core.config import get_settings
from app.services.event_bus import EventBus, Event, get_event_bus

logger = structlog.get_logger()
router = APIRouter()

# Connected clients
connected_clients: Dict[str, WebSocket] = {}


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.event_bus: EventBus = None
        self._heartbeat_task = None

    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        connected_clients[client_id] = websocket
        logger.info("websocket_connected", client_id=client_id)

    def disconnect(self, websocket: WebSocket, client_id: str) -> None:
        """Remove a WebSocket connection."""
        self.active_connections.discard(websocket)
        connected_clients.pop(client_id, None)
        logger.info("websocket_disconnected", client_id=client_id)

    async def broadcast(self, message: dict) -> None:
        """Broadcast a message to all connected clients."""
        if not self.active_connections:
            return

        message_str = json.dumps(message, default=str)
        disconnected = set()

        for connection in self.active_connections:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.warning("websocket_send_error", error=str(e))
                disconnected.add(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            self.active_connections.discard(conn)

    async def send_to_client(self, client_id: str, message: dict) -> bool:
        """Send a message to a specific client."""
        websocket = connected_clients.get(client_id)
        if not websocket:
            return False

        try:
            await websocket.send_text(json.dumps(message, default=str))
            return True
        except Exception as e:
            logger.warning("websocket_send_error", client_id=client_id, error=str(e))
            return False

    async def handle_event(self, event: Event) -> None:
        """Handle an event from the event bus and broadcast it."""
        message = {
            "type": event.type.value,
            "timestamp": event.timestamp.isoformat(),
            "payload": event.payload
        }
        await self.broadcast(message)

    async def start_heartbeat(self) -> None:
        """Start the heartbeat loop."""
        while True:
            try:
                await asyncio.sleep(30)  # Send heartbeat every 30 seconds
                message = {
                    "type": "heartbeat",
                    "timestamp": datetime.utcnow().isoformat(),
                    "payload": {
                        "connected_clients": len(self.active_connections)
                    }
                }
                await self.broadcast(message)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("heartbeat_error", error=str(e))

    async def setup_event_bus(self) -> None:
        """Subscribe to event bus for broadcasting events."""
        if self.event_bus:
            return

        self.event_bus = get_event_bus()
        await self.event_bus.subscribe_all(self.handle_event)

        # Start heartbeat
        self._heartbeat_task = asyncio.create_task(self.start_heartbeat())


# Global connection manager
manager = ConnectionManager()


def authenticate_token(token: str) -> str:
    """Authenticate WebSocket connection token."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.auth.secret_key,
            algorithms=[settings.auth.algorithm]
        )
        username = payload.get("sub")
        if username is None:
            return None
        return username
    except JWTError:
        return None


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates.

    Connection flow:
    1. Client connects to /ws
    2. Client sends authentication message: {"type": "authenticate", "token": "..."}
    3. Server validates token and confirms connection
    4. Server broadcasts events to all authenticated clients
    """
    client_id = None
    authenticated = False

    try:
        await websocket.accept()

        # Wait for authentication message
        try:
            auth_data = await asyncio.wait_for(
                websocket.receive_json(),
                timeout=10.0
            )
        except asyncio.TimeoutError:
            await websocket.send_json({
                "type": "error",
                "payload": {"message": "Authentication timeout"}
            })
            await websocket.close()
            return

        if auth_data.get("type") != "authenticate":
            await websocket.send_json({
                "type": "error",
                "payload": {"message": "Expected authentication message"}
            })
            await websocket.close()
            return

        token = auth_data.get("token")
        if not token:
            await websocket.send_json({
                "type": "error",
                "payload": {"message": "Token required"}
            })
            await websocket.close()
            return

        # Validate token
        username = authenticate_token(token)
        if not username:
            await websocket.send_json({
                "type": "error",
                "payload": {"message": "Invalid token"}
            })
            await websocket.close()
            return

        # Authentication successful
        client_id = f"{username}_{id(websocket)}"
        authenticated = True

        # Set up event bus if not already done
        await manager.setup_event_bus()

        # Add to connected clients
        manager.active_connections.add(websocket)
        connected_clients[client_id] = websocket

        # Send confirmation
        await websocket.send_json({
            "type": "authenticated",
            "timestamp": datetime.utcnow().isoformat(),
            "payload": {
                "username": username,
                "client_id": client_id
            }
        })

        logger.info("websocket_authenticated", client_id=client_id, username=username)

        # Keep connection alive and handle incoming messages
        while True:
            try:
                data = await websocket.receive_json()

                # Handle ping/pong
                if data.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    })

                # Handle subscription requests (future enhancement)
                elif data.get("type") == "subscribe":
                    # Could implement channel-based subscriptions
                    pass

            except WebSocketDisconnect:
                break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("websocket_error", error=str(e))
    finally:
        if authenticated and client_id:
            manager.disconnect(websocket, client_id)


@router.get("/ws/clients")
async def get_connected_clients():
    """Get count of connected WebSocket clients (for debugging)."""
    return {
        "connected_clients": len(manager.active_connections),
        "client_ids": list(connected_clients.keys())
    }
