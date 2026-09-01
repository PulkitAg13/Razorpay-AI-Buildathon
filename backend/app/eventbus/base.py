"""
RECOVERX AI — Event Bus Abstract Base
Defines the publish/subscribe interface for real-time event streaming.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Callable


class EventBus(ABC):
    """
    Abstract event bus for real-time agent activity streaming.

    Consumers (e.g. WebSocket handlers) subscribe to channels.
    Producers (agents, orchestrator) publish events to channels.
    """

    @abstractmethod
    async def publish(self, channel: str, event: dict[str, Any]) -> None:
        """Publish an event dict to a named channel."""
        ...

    @abstractmethod
    async def subscribe(self, channel: str) -> AsyncIterator[dict[str, Any]]:
        """
        Async generator that yields events published to the channel.
        Consumers should iterate: async for event in bus.subscribe("live"):
        """
        ...

    @abstractmethod
    async def get_recent(self, channel: str, limit: int = 50) -> list[dict[str, Any]]:
        """Return the most recent N events on a channel (for new subscribers)."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Shutdown and release resources."""
        ...
