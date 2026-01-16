"""
Redis client for caching race data and nonce storage.
"""
import json
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from redis.asyncio import Redis


# Global redis client
_redis_client: "Redis | None" = None


async def get_redis() -> "Redis":
    """Get or create Redis connection."""
    global _redis_client
    if _redis_client is None:
        import redis.asyncio as redis
        from app.config import get_settings
        settings = get_settings()
        _redis_client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def close_redis() -> None:
    """Close Redis connection."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None


class RaceCache:
    """Cache for active race data with short TTL."""

    @staticmethod
    def _key(event_id: str) -> str:
        return f"race:current:{event_id}"

    @classmethod
    async def get(cls, event_id: str) -> dict[str, Any] | None:
        """Get cached race data for an event."""
        client = await get_redis()
        data = await client.get(cls._key(event_id))
        return json.loads(data) if data else None

    @classmethod
    async def set(cls, event_id: str, data: dict[str, Any]) -> None:
        """Cache race data with 1-second TTL."""
        from app.config import get_settings
        settings = get_settings()
        client = await get_redis()
        await client.setex(
            cls._key(event_id),
            settings.redis_cache_ttl,
            json.dumps(data),
        )

    @classmethod
    async def delete(cls, event_id: str) -> None:
        """Clear cached race data."""
        client = await get_redis()
        await client.delete(cls._key(event_id))


class NonceStore:
    """Store for tracking used nonces (replay protection)."""

    @staticmethod
    def _key(device_id: str, nonce: str) -> str:
        return f"nonce:{device_id}:{nonce}"

    @classmethod
    async def check_and_store(cls, device_id: str, nonce: str) -> bool:
        """
        Check if nonce has been used and store it if not.
        Returns True if nonce is valid (not seen before).
        Returns False if nonce was already used (replay attack).
        """
        from app.config import get_settings
        settings = get_settings()
        client = await get_redis()
        key = cls._key(device_id, nonce)

        # Try to set with NX (only if not exists)
        result = await client.set(
            key,
            "1",
            ex=settings.nonce_cache_ttl_seconds,
            nx=True,
        )

        # Returns True if key was set (nonce is new)
        return result is not None


class RateLimiter:
    """Simple sliding window rate limiter."""

    @staticmethod
    def _key(identifier: str, window: str) -> str:
        return f"ratelimit:{identifier}:{window}"

    @classmethod
    async def check(
        cls,
        identifier: str,
        limit: int,
        window_seconds: int = 60,
    ) -> tuple[bool, int]:
        """
        Check rate limit for an identifier.
        Returns (allowed, remaining_requests).
        """
        import time

        client = await get_redis()
        window = str(int(time.time()) // window_seconds)
        key = cls._key(identifier, window)

        # Increment counter
        count = await client.incr(key)

        # Set expiry on first request in window
        if count == 1:
            await client.expire(key, window_seconds)

        remaining = max(0, limit - count)
        allowed = count <= limit

        return allowed, remaining
