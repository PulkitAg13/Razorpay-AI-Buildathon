"""RECOVERX AI — Event Bus package."""
from functools import lru_cache

from app.eventbus.base import EventBus
from app.eventbus.inmemory import InMemoryEventBus


@lru_cache(maxsize=1)
def get_event_bus() -> EventBus:
    """Return the configured event bus singleton."""
    from app.config import get_settings
    settings = get_settings()
    if settings.event_bus == "redis":
        try:
            from app.eventbus.redis_bus import RedisEventBus
            import logging
            logging.getLogger(__name__).info("[EventBus] Using RedisEventBus.")
            return RedisEventBus(settings.redis_url)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(f"[EventBus] Redis init failed ({exc}), falling back to InMemory.")
    return InMemoryEventBus()


__all__ = ["EventBus", "InMemoryEventBus", "get_event_bus"]
