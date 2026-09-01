"""
RECOVERX AI — In-Memory Event Bus
Async pub/sub using asyncio.Queue — no Redis required.
Default for local development.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict, deque
from typing import Any, AsyncIterator

from app.eventbus.base import EventBus

logger = logging.getLogger(__name__)

# Global buffer per channel — keeps last 200 events in memory
_BUFFER_SIZE = 200


class InMemoryEventBus(EventBus):
    """
    Thread-safe, async in-memory publish/subscribe event bus.

    - Supports multiple subscribers per channel
    - Buffers recent events for late-joining subscribers
    - Zero dependencies — works without Redis
    """

    def __init__(self) -> None:
        # channel → list of subscriber queues
        self._subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)
        # channel → circular buffer of recent events
        self._buffers: dict[str, deque[dict[str, Any]]] = defaultdict(
            lambda: deque(maxlen=_BUFFER_SIZE)
        )
        self._lock = asyncio.Lock()

    async def publish(self, channel: str, event: dict[str, Any]) -> None:
        """Publish an event to all subscribers on the channel."""
        import time
        event.setdefault("_ts", time.time())
        event.setdefault("_channel", channel)

        async with self._lock:
            self._buffers[channel].append(event)
            dead_queues = []
            for q in self._subscribers[channel]:
                try:
                    q.put_nowait(event)
                except asyncio.QueueFull:
                    dead_queues.append(q)
            for q in dead_queues:
                self._subscribers[channel].remove(q)

        logger.debug(f"[EventBus] Published to '{channel}': {event.get('type', '?')}")

    async def subscribe(self, channel: str) -> AsyncIterator[dict[str, Any]]:
        """
        Async generator — yields events as they are published.
        Starts by replaying the recent buffer, then listens live.
        """
        q: asyncio.Queue = asyncio.Queue(maxsize=500)

        async with self._lock:
            # Replay buffer
            for buffered_event in list(self._buffers[channel]):
                await q.put(buffered_event)
            self._subscribers[channel].append(q)

        try:
            while True:
                event = await q.get()
                yield event
        finally:
            async with self._lock:
                try:
                    self._subscribers[channel].remove(q)
                except ValueError:
                    pass

    async def get_recent(self, channel: str, limit: int = 50) -> list[dict[str, Any]]:
        """Return the most recent N events without subscribing."""
        async with self._lock:
            buf = list(self._buffers[channel])
        return buf[-limit:]

    async def close(self) -> None:
        """Signal all subscribers to stop (by closing their queues conceptually)."""
        async with self._lock:
            self._subscribers.clear()
            self._buffers.clear()
        logger.info("[EventBus] InMemoryEventBus closed.")
