"""
RECOVERX AI — Redis Event Bus (optional)
Enabled when EVENT_BUS=redis in .env.
Falls back to InMemoryEventBus if Redis is unavailable.
"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator

from app.eventbus.base import EventBus

logger = logging.getLogger(__name__)


class RedisEventBus(EventBus):
    """
    Redis pub/sub event bus using the async redis client.
    Requires: pip install redis[asyncio]
    Enable: EVENT_BUS=redis in .env
    """

    def __init__(self, redis_url: str) -> None:
        self._url = redis_url
        self._client = None
        self._pubsub = None
        self._init_client()

    def _init_client(self) -> None:
        try:
            import redis.asyncio as aioredis
            self._client = aioredis.from_url(self._url, decode_responses=True)
        except ImportError:
            logger.warning("[RedisEventBus] redis package not installed. Falling back to in-memory.")
            self._client = None
        except Exception as exc:
            logger.warning(f"[RedisEventBus] Connection failed: {exc}")
            self._client = None

    async def publish(self, channel: str, event: dict[str, Any]) -> None:
        if self._client is None:
            return
        await self._client.publish(channel, json.dumps(event))

    async def subscribe(self, channel: str) -> AsyncIterator[dict[str, Any]]:
        if self._client is None:
            return
        pubsub = self._client.pubsub()
        await pubsub.subscribe(channel)
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        yield json.loads(message["data"])
                    except json.JSONDecodeError:
                        pass
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()

    async def get_recent(self, channel: str, limit: int = 50) -> list[dict[str, Any]]:
        """Redis doesn't natively buffer; use a sorted set with score=timestamp."""
        if self._client is None:
            return []
        try:
            raw = await self._client.lrange(f"buf:{channel}", -limit, -1)
            return [json.loads(r) for r in raw]
        except Exception:
            return []

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
