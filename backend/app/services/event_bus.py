"""
Event Bus
=========

In-memory event bus for inter-component communication.
"""

import asyncio
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional
from dataclasses import dataclass, field
import structlog

logger = structlog.get_logger()


class EventType(str, Enum):
    """Event types for the event bus."""
    # Status events
    STATUS_CHANGE = "status_change"
    HEARTBEAT = "heartbeat"

    # Repository events
    REPO_CHANGE_DETECTED = "repo_change_detected"
    REPO_POLL_ERROR = "repo_poll_error"

    # Update events
    UPDATE_STARTED = "update_started"
    UPDATE_COMPLETED = "update_completed"
    UPDATE_FAILED = "update_failed"
    UPDATE_ROLLED_BACK = "update_rolled_back"

    # Error events
    ERROR_DETECTED = "error_detected"
    ERROR_RESOLVED = "error_resolved"
    ERROR_IGNORED = "error_ignored"

    # Fix events
    FIX_STARTED = "fix_started"
    FIX_PROGRESS = "fix_progress"
    FIX_COMPLETED = "fix_completed"
    FIX_FAILED = "fix_failed"
    FIX_ESCALATED = "fix_escalated"


@dataclass
class Event:
    """Event object for the event bus."""
    type: EventType
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "type": self.type.value,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
        }


# Type alias for event handlers
EventHandler = Callable[[Event], Coroutine[Any, Any, None]]


class EventBus:
    """
    In-memory async event bus for component communication.

    Supports:
    - Pub/sub pattern with multiple subscribers per event type
    - Async event handlers
    - Event history for late subscribers
    """

    def __init__(self, history_size: int = 100):
        self._subscribers: Dict[EventType, List[EventHandler]] = {}
        self._global_subscribers: List[EventHandler] = []
        self._history: List[Event] = []
        self._history_size = history_size
        self._lock = asyncio.Lock()

    async def subscribe(
        self,
        event_type: EventType,
        handler: EventHandler
    ) -> None:
        """Subscribe to a specific event type."""
        async with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(handler)
            logger.debug("subscriber_added", event_type=event_type.value)

    async def subscribe_all(self, handler: EventHandler) -> None:
        """Subscribe to all event types."""
        async with self._lock:
            self._global_subscribers.append(handler)
            logger.debug("global_subscriber_added")

    async def unsubscribe(
        self,
        event_type: EventType,
        handler: EventHandler
    ) -> None:
        """Unsubscribe from a specific event type."""
        async with self._lock:
            if event_type in self._subscribers:
                try:
                    self._subscribers[event_type].remove(handler)
                except ValueError:
                    pass

    async def publish(self, event: Event) -> None:
        """Publish an event to all subscribers."""
        async with self._lock:
            # Add to history
            self._history.append(event)
            if len(self._history) > self._history_size:
                self._history.pop(0)

            # Get handlers
            handlers = list(self._global_subscribers)
            if event.type in self._subscribers:
                handlers.extend(self._subscribers[event.type])

        # Call handlers outside of lock
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(
                    "event_handler_error",
                    event_type=event.type.value,
                    error=str(e)
                )

        logger.debug(
            "event_published",
            event_type=event.type.value,
            handlers_called=len(handlers)
        )

    async def emit(
        self,
        event_type: EventType,
        payload: Dict[str, Any],
        source: str = "unknown"
    ) -> None:
        """Convenience method to create and publish an event."""
        event = Event(type=event_type, payload=payload, source=source)
        await self.publish(event)

    def get_history(
        self,
        event_type: Optional[EventType] = None,
        limit: int = 50
    ) -> List[Event]:
        """Get recent event history."""
        if event_type:
            filtered = [e for e in self._history if e.type == event_type]
            return filtered[-limit:]
        return self._history[-limit:]


# Global event bus instance
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus
